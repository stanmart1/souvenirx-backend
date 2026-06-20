# SouvenirX — Developer Quick Reference

## Project Structure

```
souvenirx-backend/     FastAPI + SQLAlchemy (async) + PostgreSQL
souvenirx-frontend/    React + TanStack Router + Vite + TailwindCSS
```

## Common Commands

### Backend

```bash
cd souvenirx-backend
source .venv/bin/activate
python3 -m pytest tests/ -v          # Run tests
python3 -m py_compile app/main.py    # Syntax check
alembic upgrade head                 # Run migrations
alembic downgrade -1                 # Roll back last migration
```

### Frontend

```bash
cd souvenirx-frontend
npm run test                         # Run vitest
npx eslint src/                      # Lint
npx prettier --write src/            # Format
npm run dev                          # Dev server
```

## RBAC Architecture

### Data Model

```
users ──< user_roles >── roles ──< role_permissions >── permissions
```

- **Users** have multiple **Roles** via `user_roles` (tracks `assigned_by`).
- **Roles** have multiple **Permissions** via `role_permissions`.
- **Permissions** are `resource:action` pairs (e.g., `users:read`).
- Wildcards: `*:*` (all), `users:*` (all on users), `*:read` (read all).

### Key Files

| File | Purpose |
|------|---------|
| `app/models/rbac.py` | Role, Permission, user_roles, role_permissions models |
| `app/services/rbac.py` | All RBAC service functions (CRUD, assignment, checks) |
| `app/middleware/permissions.py` | `require_permission()` dependency, `user_has_permission()` |
| `app/middleware/auth.py` | `get_current_admin`, `get_current_user` |
| `app/routes/admin_rbac.py` | RBAC management API (16 endpoints under `/api/admin/rbac`) |
| `app/routes/admin.py` | Main admin API (uses `get_current_admin` as mount-level guard) |
| `app/services/audit.py` | `log_audit()` for audit trail |
| `app/models/audit_log.py` | AuditLog model |
| `app/schemas/rbac.py` | Pydantic schemas for RBAC API |
| `docs/RBAC_GUIDE.md` | Full RBAC documentation |

### Frontend RBAC Files

| File | Purpose |
|------|---------|
| `src/lib/auth.tsx` | `useAuth()` context with `hasPermission()`, `isAdmin` |
| `src/lib/useCan.ts` | `useCan()` hook for permission checks |
| `src/components/admin/Can.tsx` | `<Can>` component for conditional rendering |
| `src/components/admin/PermissionMatrix.tsx` | Permission grid for role editing |
| `src/components/admin/RoleEditor.tsx` | Role create/edit modal |
| `src/routes/admin.roles.tsx` | Roles & Permissions management page |
| `src/components/dashboard/AdminSidebar.tsx` | Nav with permission-based filtering |

### Permission Enforcement Pattern

1. **Mount-level guard**: `admin.tsx` checks `isAdmin` (user has "admin" role).
2. **Endpoint-level guard**: RBAC endpoints use `require_permission("roles:read")` etc.
3. **Page-level guard**: Pages check `hasPermission("roles:read")` and show error if denied.
4. **Nav-level guard**: Sidebar filters items by `permission` field.
5. **Action-level guard**: Use `<Can permission="users:delete">` or `useCan()` hook.

### Adding a New Admin Endpoint with Permission Check

```python
from app.middleware.permissions import require_permission

@router.post("/things", dependencies=[Depends(require_permission("things:write"))])
async def create_thing(...):
    ...
```

### Adding a New Permission

1. Insert into the `permissions` table (or use `create_permission()` service function).
2. Grant to roles via `grant_permission()` or the admin UI.
3. Use in endpoints via `require_permission("things:write")`.
4. Use in frontend via `hasPermission("things:write")` or `<Can>`.

## Testing

- Backend tests use `pytest` with `pytest-asyncio` and `unittest.mock.AsyncMock`.
- Frontend tests use `vitest` with `@testing-library/react`.
- Always run both test suites before committing RBAC changes.
