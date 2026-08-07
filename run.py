"""IFMS 一键启动 — 单窗口，Ctrl+C 统一关闭所有子进程"""
import subprocess, sys, os, time, webbrowser, re
from threading import Thread

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_PORT = int(os.getenv("IFMS_PORT", "8000"))
FRONTEND_PORT = 5173
SKIP_FRONTEND = os.getenv("IFMS_SKIP_FRONTEND", "") == "1"


def _free_port(port: int):
    """Windows：自动杀掉占用指定端口的旧进程，避免启动时端口冲突"""
    if sys.platform != "win32":
        return  # 本函数仅面向 Windows
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], text=True, timeout=5
        )
        for line in out.splitlines():
            if "LISTENING" not in line:
                continue
            # netstat 格式: Proto  Local Address  Foreign Address  State  PID
            # 取第二列 (Local Address)，从中提取端口
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            addr = parts[1]  # e.g. "0.0.0.0:8000" or "[::]:8000"
            colon = addr.rfind(":")
            if colon < 0:
                continue
            if addr[colon + 1:] == str(port):
                pid = parts[-1]
                if pid.isdigit():
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        capture_output=True,
                    )
                    print(f"  (已释放端口 {port}，旧进程 PID {pid})")
                    time.sleep(1)
    except FileNotFoundError:
        pass  # netstat 或 taskkill 不可用时静默跳过
    except Exception:
        pass  # 其他异常也不阻塞启动


def _kill_tree(proc):
    """Windows: 用 taskkill /T 杀掉进程树，避免孤儿进程"""
    if proc and proc.poll() is None:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
        )


def main():
    print("=" * 50)
    print("  事项反馈系统 (IFMS)")
    print("=" * 50)

    # --- 后端 ---
    _free_port(BACKEND_PORT)  # 自动清理旧进程占用的端口
    print(f"\n[1/2] 启动后端 (端口 {BACKEND_PORT})...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "0.0.0.0", "--port", str(BACKEND_PORT)],
        cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )

    # --- 前端 ---
    if SKIP_FRONTEND:
        print("   跳过前端（IFMS_SKIP_FRONTEND=1），后端将托管 frontend/dist")
        frontend = None
    else:
        print(f"[2/2] 启动前端 (端口 {FRONTEND_PORT})...")
        try:
            frontend = subprocess.Popen(
                ["npm.cmd", "run", "dev", "--", "--host", "0.0.0.0",
                 "--port", str(FRONTEND_PORT)],
                cwd=os.path.join(ROOT, "frontend"),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            time.sleep(5)  # 给 Vite 足够的冷启动时间
            if frontend.poll() is not None:
                print("   前端启动失败 — 请确认已执行 npm install 且 Node.js 可用")
                frontend = None
        except FileNotFoundError:
            print("   npm 未找到，跳过前端（请安装 Node.js）")
            frontend = None

    print()
    if frontend:
        print(f"  前端: http://localhost:{FRONTEND_PORT}")
    else:
        print(f"  访问: http://localhost:{BACKEND_PORT}")
    print(f"  后端: http://localhost:{BACKEND_PORT}")
    print(f"  API:  http://localhost:{BACKEND_PORT}/docs")
    print()
    print("  Ctrl+C 停止所有服务")
    print("=" * 50)

    # 后台线程读取子进程输出（避免管道阻塞）
    def _forward(proc, tag):
        try:
            for line in proc.stdout:
                print(f"[{tag}] {line.rstrip()}")
        except Exception:
            pass  # 管道关闭时正常退出

    Thread(target=_forward, args=(backend, "backend"), daemon=True).start()
    if frontend:
        Thread(target=_forward, args=(frontend, "frontend"), daemon=True).start()

    # 打开浏览器
    time.sleep(2)
    url = f"http://localhost:{FRONTEND_PORT}" if frontend else f"http://localhost:{BACKEND_PORT}"
    webbrowser.open(url)

    try:
        while backend.poll() is None:
            if frontend and frontend.poll() is not None:
                print("[warning] 前端进程已退出")
                frontend = None
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭...")
    finally:
        _kill_tree(backend)
        if frontend:
            _kill_tree(frontend)
        print("已停止所有服务。")


if __name__ == "__main__":
    main()
