---
name: feedbacksystem-maintainer
description: Maintain and harden the feedbacksystem repository (FastAPI backend, Vue frontend, SQLite data). Use when tasks involve API authorization fixes, permission boundary enforcement, secure file upload/export behavior, schema/endpoint consistency with requirement docs, regression test updates, or release-ready refactors for this project.
---

# Feedbacksystem Maintainer

## Quick Workflow
1. Read requirement deltas from `事项反馈系统_最终需求文档.md` and locate affected routes/models.
2. Enforce server-side authorization using `current_user`; never trust frontend role/user parameters for permissions.
3. Implement minimal safe changes first in `backend/` (auth, routers, schema constraints), then align `frontend/` calls.
4. Add or update tests under `backend/tests/` for authz and behavior regressions.
5. Run `pytest -q` before finalizing.

## Project-Specific Rules
- Treat `backend/auth.py`, `backend/routers/*.py`, and `backend/models.py` as security-critical.
- Prefer backward-compatible API changes unless user explicitly accepts breaking changes.
- Keep changes incremental and verify each batch with tests.
- If requirement doc and implementation conflict, either:
  - implement missing behavior, or
  - update docs and call out the decision explicitly.

## Validation Checklist
- Authentication: protected endpoints require valid Bearer token.
- Authorization: only permitted users can view/update/delete target resources.
- Data safety: no password hash export, no dangerous file path handling.
- Regression: existing item creation/feedback/todo flows still pass.

## References
- Security checklist: `references/security-checklist.md`
- Test matrix: `references/test-matrix.md`

## Deliverable Style
- Provide concrete file paths and changed behavior.
- Include risk notes and what remains for P1/P2 hardening.
