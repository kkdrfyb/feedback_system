import argparse
import json
import os
import sqlite3
import statistics
import time
from typing import Any, Dict


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _required_tables_present(conn: sqlite3.Connection) -> bool:
    required = ["items", "item_users", "feedbacks", "operation_logs"]
    return all(_table_exists(conn, name) for name in required)


def _pick_sample_ids(conn: sqlite3.Connection):
    creator_id_row = conn.execute("SELECT creator_id FROM items WHERE creator_id IS NOT NULL LIMIT 1").fetchone()
    creator_id = creator_id_row[0] if creator_id_row else 1

    user_id_row = conn.execute("SELECT user_id FROM item_users WHERE user_id IS NOT NULL LIMIT 1").fetchone()
    user_id = user_id_row[0] if user_id_row else 1

    item_id_row = conn.execute("SELECT id FROM items LIMIT 1").fetchone()
    item_id = item_id_row[0] if item_id_row else 1
    return creator_id, user_id, item_id


def _run_query(conn: sqlite3.Connection, sql: str, params: tuple, loops: int):
    durations = []
    for _ in range(loops):
        t0 = time.perf_counter()
        conn.execute(sql, params).fetchall()
        durations.append((time.perf_counter() - t0) * 1000.0)
    durations.sort()
    return {
        "avg_ms": round(statistics.mean(durations), 3),
        "p95_ms": round(durations[int(len(durations) * 0.95) - 1], 3),
        "min_ms": round(durations[0], 3),
        "max_ms": round(durations[-1], 3),
        "loops": loops,
    }


def _load_report(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _to_pct_delta(current: float, baseline: float):
    if baseline <= 0:
        return None
    return round(((current - baseline) / baseline) * 100.0, 2)


def _print_comparison(current: Dict[str, Any], baseline: Dict[str, Any], fail_on_regress_pct: float) -> int:
    baseline_queries = baseline.get("queries", {})
    current_queries = current.get("queries", {})
    regressions = []

    print("\nBenchmark Comparison (current vs baseline)")
    for query_name, current_metrics in current_queries.items():
        if query_name not in baseline_queries:
            print(f"{query_name}: baseline missing, skipped")
            continue

        baseline_metrics = baseline_queries[query_name]
        current_avg = float(current_metrics.get("avg_ms", 0.0))
        baseline_avg = float(baseline_metrics.get("avg_ms", 0.0))
        avg_delta_pct = _to_pct_delta(current_avg, baseline_avg)

        current_p95 = float(current_metrics.get("p95_ms", 0.0))
        baseline_p95 = float(baseline_metrics.get("p95_ms", 0.0))
        p95_delta_pct = _to_pct_delta(current_p95, baseline_p95)

        avg_delta_text = "n/a" if avg_delta_pct is None else f"{avg_delta_pct:+.2f}%"
        p95_delta_text = "n/a" if p95_delta_pct is None else f"{p95_delta_pct:+.2f}%"
        print(
            f"{query_name}: avg {baseline_avg} -> {current_avg} ms ({avg_delta_text}), "
            f"p95 {baseline_p95} -> {current_p95} ms ({p95_delta_text})"
        )

        if fail_on_regress_pct > 0:
            if avg_delta_pct is not None and avg_delta_pct > fail_on_regress_pct:
                regressions.append((query_name, "avg_ms", avg_delta_pct))
            if p95_delta_pct is not None and p95_delta_pct > fail_on_regress_pct:
                regressions.append((query_name, "p95_ms", p95_delta_pct))

    if regressions:
        print("\nRegressions above threshold:")
        for query_name, metric, delta in regressions:
            print(f"- {query_name}.{metric}: +{delta:.2f}%")
        return 2
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark hot query paths for feedback system.")
    default_db = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "feedback.db"))
    parser.add_argument("--db", default=default_db, help="Path to sqlite db file (default: backend/feedback.db)")
    parser.add_argument("--loops", type=int, default=200, help="Loops per query (default: 200)")
    parser.add_argument("--json-out", default="", help="Optional JSON file output path")
    parser.add_argument("--compare-with", default="", help="Optional baseline JSON report path for comparison")
    parser.add_argument(
        "--fail-on-regress-pct",
        type=float,
        default=0.0,
        help="Fail with exit code 2 if avg/p95 regression exceeds this percent (default: disabled)",
    )
    parser.add_argument("--explain", action="store_true", help="Print EXPLAIN QUERY PLAN for each query")
    args = parser.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"Database file not found: {args.db}")

    conn = sqlite3.connect(args.db)
    try:
        if not _required_tables_present(conn):
            raise SystemExit("Missing required tables for benchmark.")

        creator_id, user_id, item_id = _pick_sample_ids(conn)

        query_specs = [
            (
                "items_by_creator",
                "SELECT id, title, status, created_at FROM items WHERE creator_id = ? ORDER BY created_at DESC LIMIT 20",
                (creator_id,),
            ),
            (
                "items_by_participant",
                """
                SELECT i.id, i.title, i.status, i.deadline
                FROM items i
                JOIN item_users iu ON iu.item_id = i.id
                WHERE iu.user_id = ?
                ORDER BY i.created_at DESC
                LIMIT 20
                """,
                (user_id,),
            ),
            (
                "todos_pending",
                "SELECT id, item_id, user_id FROM item_users WHERE user_id = ? AND feedback_status = 'pending' LIMIT 50",
                (user_id,),
            ),
            (
                "item_feedback_progress",
                """
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN feedback_status IN ('done', 'completed') THEN 1 ELSE 0 END) AS done_count
                FROM item_users
                WHERE item_id = ?
                """,
                (item_id,),
            ),
            (
                "operation_logs_latest",
                "SELECT id, user_id, action, timestamp FROM operation_logs ORDER BY timestamp DESC LIMIT 100",
                (),
            ),
        ]

        report = {
            "db": args.db,
            "loops": args.loops,
            "sample_ids": {"creator_id": creator_id, "user_id": user_id, "item_id": item_id},
            "queries": {},
        }

        for name, sql, params in query_specs:
            if args.explain:
                explain_rows = conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
                print(f"\n[{name}] EXPLAIN")
                for row in explain_rows:
                    print(row)
            report["queries"][name] = _run_query(conn, sql, params, args.loops)

        print("Query Benchmark Report")
        print(f"db: {report['db']}")
        print(f"loops: {report['loops']}")
        for name, metrics in report["queries"].items():
            print(
                f"{name}: avg={metrics['avg_ms']}ms p95={metrics['p95_ms']}ms "
                f"min={metrics['min_ms']}ms max={metrics['max_ms']}ms"
            )

        if args.json_out:
            out_path = os.path.abspath(args.json_out)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"JSON report saved to: {out_path}")

        if args.compare_with:
            baseline_path = os.path.abspath(args.compare_with)
            if not os.path.exists(baseline_path):
                raise SystemExit(f"Baseline report not found: {baseline_path}")
            baseline_report = _load_report(baseline_path)
            exit_code = _print_comparison(report, baseline_report, args.fail_on_regress_pct)
            if exit_code != 0:
                raise SystemExit(exit_code)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
