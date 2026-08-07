# Security Checklist

## AuthN/AuthZ
- Require `Depends(get_current_user)` on protected endpoints.
- Derive actor identity from token (`current_user`), not request params.
- Restrict admin-only endpoints explicitly.
- Enforce ownership/assignment checks on item/group/feedback operations.

## Sensitive Data
- Do not export `password_hash`.
- Do not log secrets/tokens/passwords.
- Move JWT secret to environment variable with fallback only for local dev.

## Uploads
- Sanitize filename (`basename` + character whitelist).
- Prefix filename with UUID to avoid overwrite.
- Store files under controlled `uploads/` directory only.

## Regression Targets
- Login + protected route access.
- Unauthorized group/item/feedback access denied.
- Existing happy path for create item -> todo -> submit feedback preserved.
