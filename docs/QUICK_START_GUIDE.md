# Quick Start Guide: Security & Feature Upgrade

**For Developers Starting This Project**

---

## 📋 What You Need to Know

### The Situation
- ✅ Auth system fixed (9 bugs resolved)
- ❌ Email verification has security holes
- ❌ Admin dashboard missing critical features
- ❌ No audit logging (compliance risk)

### The Goal
Harden security and add essential admin features in 3-4 weeks.

---

## 🚀 Getting Started

### 1. Read These Files (in order)

1. **UPGRADE_SUMMARY.md** (5 min) - Executive overview
2. **EMAIL_VERIFICATION_AND_USER_MANAGEMENT_AUDIT.md** (20 min) - Detailed findings
3. **IMPLEMENTATION_PLAN.md** (30 min) - Task-by-task guide with code
4. **AUTH_FIXES_SUMMARY.md** (10 min) - What's already fixed

### 2. Set Up Your Environment

```bash
# Backend
cd souvenirx-backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Frontend
cd souvenirx-frontend
npm install

# Database
# Make sure PostgreSQL is running
# Update .env with your database credentials
```

### 3. Create Feature Branch

```bash
git checkout -b feature/security-upgrade
```

---

## 📅 Week-by-Week Breakdown

### Week 1: Critical Security 🔴

**Goal:** Fix security vulnerabilities

**Tasks:**
1. Add token expiration to email verification (Day 1-2)
2. Build audit logging system (Day 3-4)
3. Fix multi-role user bug (Day 5)

**Files to modify:**
- `app/models/user.py` - Add expiration field
- `app/models/audit_log.py` - NEW file
- `app/routes/auth.py` - Add expiration checks
- `app/routes/admin.py` - Fix queries, add logging
- `app/services/audit.py` - NEW file

**Deliverables:**
- All verification tokens expire in 24 hours
- All admin actions logged to database
- Multi-role users work correctly

---

### Week 2: Critical Features 🔴

**Goal:** Add essential admin capabilities

**Tasks:**
1. Admin password reset (Day 1-2)
2. Role management system (Day 3-4)
3. User deletion (Day 5)
4. Email verification management (Day 6-7)

**Files to modify:**
- `app/routes/admin.py` - New endpoints
- `src/routes/admin.customers.tsx` - UI updates
- `src/routes/admin.users.tsx` - NEW page
- `app/data/email_templates.py` - New template

**Deliverables:**
- Admins can reset customer passwords
- Admins can manage user roles
- Admins can delete users
- Admins can manually verify emails

---

### Week 3: Enhanced Features 🟡

**Goal:** Improve usability and security

**Tasks:**
1. Bulk operations (Day 1-2)
2. Email verification enforcement (Day 3-4)
3. Input validation & rate limiting (Day 5)

**Files to modify:**
- `app/routes/admin.py` - Bulk endpoint
- `app/middleware/auth.py` - Verification middleware
- `src/routes/admin.users.tsx` - Bulk UI
- `src/components/site/Header.tsx` - Verification banner

**Deliverables:**
- Bulk user operations work
- Checkout requires verified email
- All inputs validated
- Rate limiting active

---

### Week 4: Polish & Deploy 🟢

**Goal:** Optimize, test, document

**Tasks:**
1. Query optimization (Day 1-2)
2. CSV streaming (Day 3)
3. Advanced filters (Day 4-5)
4. Testing & docs (Day 6-7)

**Files to modify:**
- `app/routes/admin.py` - Optimize queries
- `tests/test_*.py` - NEW test files
- `docs/API.md` - Documentation
- `docs/ADMIN_GUIDE.md` - NEW guide

**Deliverables:**
- Fast queries (<500ms)
- All tests passing
- Complete documentation
- Ready for production

---

## 🔧 Development Workflow

### Daily Routine

```bash
# 1. Pull latest changes
git pull origin main

# 2. Create task branch
git checkout -b task/add-token-expiration

# 3. Make changes (see IMPLEMENTATION_PLAN.md for code)

# 4. Test locally
# Backend: pytest
# Frontend: npm run dev

# 5. Commit with descriptive message
git add .
git commit -m "Add 24-hour expiration to verification tokens"

# 6. Push and create PR
git push origin task/add-token-expiration
# Create PR on GitHub/GitLab

# 7. After review, merge to feature branch
git checkout feature/security-upgrade
git merge task/add-token-expiration
```

### Testing Checklist

Before marking any task complete:

- [ ] Code runs without errors
- [ ] Manual testing in browser/Postman
- [ ] No console errors
- [ ] Database migrations work
- [ ] Existing features still work
- [ ] Code reviewed by peer

---

## 📝 Code Examples

### Example 1: Adding Token Expiration

**File:** `app/models/user.py`

```python
# Add this field to User model
verification_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
```

**File:** `app/routes/auth.py` (registration)

```python
from datetime import timedelta

# After generating token
user.verification_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
```

**File:** `app/routes/auth.py` (verification)

```python
# In verify_email endpoint
if user.verification_token_expires_at and user.verification_token_expires_at < datetime.now(timezone.utc):
    raise HTTPException(status_code=400, detail="Verification link has expired. Please request a new one.")
```

### Example 2: Adding Audit Logging

**File:** `app/services/audit.py` (NEW)

```python
async def log_audit(db, admin_id, action, resource_type, resource_id, changes=None, ip_address=None):
    from app.models.audit_log import AuditLog
    import json
    
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        changes=json.dumps(changes) if changes else None,
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()
```

**Usage in admin endpoint:**

```python
from app.services.audit import log_audit

# After updating customer
await log_audit(
    db=db,
    admin_id=str(admin.id),
    action="update_customer",
    resource_type="user",
    resource_id=customer_id,
    changes={"old": old_values, "new": new_values},
    ip_address=request.client.host if request.client else None,
)
```

### Example 3: Fixing Multi-Role Query

**File:** `app/routes/admin.py`

```python
# Before (BROKEN)
query = select(User).where(User.role == UserRole.customer.value)

# After (FIXED)
query = select(User).where(User.role.like('%customer%'))

# Or using the helper method
query = select(User).where(User.has_role('customer'))
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Migration Fails

**Error:** `Column already exists`

**Solution:**
```bash
# Drop the migration
alembic downgrade -1

# Regenerate
alembic revision --autogenerate -m "Your message"

# Check the generated file before running
alembic upgrade head
```

### Issue 2: Import Errors

**Error:** `ModuleNotFoundError: No module named 'app.services.audit'`

**Solution:**
```bash
# Make sure __init__.py exists
touch app/services/__init__.py

# Restart your dev server
```

### Issue 3: Token Expiration Not Working

**Error:** Tokens still valid after 24 hours

**Solution:**
```python
# Check timezone usage
from datetime import timezone
datetime.now(timezone.utc)  # ✅ Correct
datetime.now()  # ❌ Wrong (no timezone)
```

### Issue 4: Audit Logs Not Appearing

**Error:** No logs in database

**Solution:**
```python
# Make sure you're calling flush/commit
await db.flush()  # ✅ After adding log
await db.commit()  # ✅ Or this

# Check the log was actually created
print(f"Created audit log: {log.id}")
```

---

## 📊 Progress Tracking

Use the todo list to track progress:

```bash
# View all tasks
devin todo list

# Mark task as in progress
devin todo update 1 --status in_progress

# Mark task as complete
devin todo update 1 --status completed
```

Or use the todo_write tool in your code editor.

---

## 🆘 Getting Help

### When Stuck

1. **Check the implementation plan** - Has code examples for every task
2. **Check the audit report** - Has detailed explanations
3. **Search existing code** - Look for similar patterns
4. **Ask the team** - Don't spend >30 min stuck

### Resources

- **Backend docs:** FastAPI docs, SQLAlchemy docs
- **Frontend docs:** React docs, TanStack Router docs
- **Database:** PostgreSQL docs, Alembic docs

---

## ✅ Definition of Done

A task is complete when:

- [ ] Code written and tested
- [ ] No errors in console/logs
- [ ] Manual testing passed
- [ ] Existing features still work
- [ ] Code reviewed
- [ ] Documentation updated (if needed)
- [ ] Committed to feature branch
- [ ] Todo item marked complete

---

## 🎯 Success Criteria

### Phase 1 Complete When:
- [ ] All tokens expire in 24 hours
- [ ] Audit logging works for all admin actions
- [ ] Multi-role users work correctly
- [ ] Tests pass

### Phase 2 Complete When:
- [ ] Admins can reset passwords
- [ ] Admins can manage roles
- [ ] Admins can delete users
- [ ] Admins can verify emails
- [ ] Tests pass

### Phase 3 Complete When:
- [ ] Bulk operations work
- [ ] Email verification enforced
- [ ] Input validation active
- [ ] Rate limiting active
- [ ] Tests pass

### Phase 4 Complete When:
- [ ] Queries optimized
- [ ] CSV export streams
- [ ] Advanced filters work
- [ ] All tests pass
- [ ] Documentation complete

---

## 🚢 Deployment Checklist

Before deploying to production:

- [ ] All phases complete
- [ ] All tests passing
- [ ] Security audit passed
- [ ] Database backup created
- [ ] Migrations tested in staging
- [ ] Documentation reviewed
- [ ] Rollback plan prepared
- [ ] Team trained on new features
- [ ] Monitoring set up
- [ ] Error tracking configured

---

## 📞 Contact

**Questions about this upgrade?**
- Check IMPLEMENTATION_PLAN.md for detailed tasks
- Check audit report for code examples
- Ask your tech lead

**Found a bug in the plan?**
- Document it
- Propose a fix
- Update the plan

---

**Good luck! You've got this! 🚀**

Remember: Security first, features second, optimization third.
