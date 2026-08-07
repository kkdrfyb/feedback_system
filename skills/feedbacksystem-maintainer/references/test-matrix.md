# Test Matrix

## Backend API
- `POST /api/login`
- `GET /api/items` with token
- `POST /api/items` + assignment
- `GET /api/todos` scoped to current user
- `POST /api/feedbacks` by assigned user

## Authorization Cases
- Non-admin cannot manage users.
- Non-admin cannot pass forged role/user params to elevate permissions.
- User cannot edit/delete items they do not own (unless admin).
- User cannot update feedback they do not own.

## Export/Upload Cases
- User export contains no password hash.
- Upload same original filename twice does not overwrite previous file.
- Path traversal filename payload is neutralized.
