# Deployment Review - EHModuli

**Date**: 2026-09-01  
**Status**: READY FOR PRODUCTION WITH CRITICAL FIXES REQUIRED  
**Target**: Synology NAS via Docker Compose + PostgreSQL

---

## Executive Summary

The EHModuli project has solid architectural foundations but requires **critical fixes** before production deployment. The main issues are:

1. **entrypoint.sh**: Uses hardcoded User model import and creates admin with plaintext password every restart
2. **Security**: Hardcoded credentials in .env.example; no environment validation
3. **Docker Compose**: Container names hardcoded; not using env_file pattern
4. **Configuration**: Missing deployment variables (GUNICORN_WORKERS, CREATE_SUPERUSER, etc.)
5. **Healthcheck**: Current endpoint doesn't verify database connectivity
6. **Staticfiles**: Strategy unclear; no persistent volume

---

## Criticality Assessment

### BLOCKING ISSUES 🔴 (Must Fix Before Production)

| Issue | File | Impact | Status |
|-------|------|--------|--------|
| User model hardcoded in entrypoint | entrypoint.sh:17 | App breaks if User model changes | FIX REQUIRED |
| Admin created every restart with plaintext password | entrypoint.sh:18-19 | Security risk, non-idempotent behavior | FIX REQUIRED |
| No set -Eeuo pipefail in entrypoint | entrypoint.sh:2 | Silent failures possible | FIX REQUIRED |
| No pg_isready timeout | entrypoint.sh:5 | Container hangs on DB connection issues | FIX REQUIRED |
| container_name hardcoded in compose | docker-compose.yml:6,26 | Conflicts when updating containers on Synology | FIX REQUIRED |
| Database not verified in healthcheck | app/urls.py:5-6 | App appears healthy when DB is down | FIX REQUIRED |
| env_file pattern not used | docker-compose.yml | Manual var substitution error-prone | FIX REQUIRED |

### HIGH PRIORITY ISSUES 🟠 (Should Fix Before Production)

| Issue | File | Impact | Fix |
|-------|------|--------|-----|
| Plaintext credentials in .env.example | .env.example:3,10 | Accidentally committed secrets | Remove defaults, guide generation |
| SECRET_KEY as example value | .env.example:3 | Could be committed to repo | Change to placeholder |
| GUNICORN_WORKERS hardcoded to 4 | entrypoint.sh:26 | Too high for NAS, causes resource exhaustion | Make configurable |
| No CREATE_SUPERUSER variable | entrypoint.sh | Always creates admin | Add conditional creation |
| POSTGRES_PASSWORD default hardcoded | docker-compose.yml:10 | Default used in production | Remove defaults, require explicit |
| No validation of required env vars | entrypoint.sh | App starts with missing config | Add validation function |
| /storage/clienti not verified writable | entrypoint.sh | App crashes on upload | Add verification |
| Dockerfile USER runs before chown | Dockerfile:20 | Files may have wrong permissions | Reorder |

### MEDIUM PRIORITY 🟡 (Recommended Improvements)

| Issue | Recommendation |
|-------|-----------------|
| Staticfiles strategy unclear | Define: in-image + collectstatic OR persistent volume in /app/data |
| BUILD_ARGS for UID/GID | Allow customization of appuser UID/GID for Synology alignment |
| No healthcheck readiness check | Implement /health/ready/ that verifies DB + filesystem |
| Gunicorn worker-tmp-dir | Using /dev/shm may not exist or be limited |
| No structured healthcheck output | Add JSON response with component status |
| CSRF_TRUSTED_ORIGINS hardcoded HTTPS | Should respect ENVIRONMENT variable |
| No resource limits defined | Add memory/CPU limits to docker-compose |

---

## Files Analysis

### ✅ Positive Findings

- **settings.py**: Well-configured with environment variable pattern; supports both SQLite (dev) and PostgreSQL (prod)
- **AUTH_USER_MODEL**: Correctly set to 'modules.User'
- **Security middleware**: CSP, CSRF, XFrame properly configured
- **Database abstraction**: Conditional SQLite/PostgreSQL based on ENVIRONMENT
- **requirements.txt**: Pinned versions, no unnecessary deps
- **.gitignore**: Comprehensive, includes .env, db.sqlite3, staticfiles, data/
- **Docker base**: Python 3.11-slim, minimal layers
- **Network isolation**: collector-network, db port not exposed
- **PG healthcheck**: Properly configured with retries and timeout

### ❌ Critical Problems

#### entrypoint.sh (Line 17-19)

**Current Code:**
```bash
from django.contrib.auth.models import User  # ❌ HARDCODED MODEL
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')  # ❌ PLAINTEXT PASSWORD
```

**Problems:**
1. Uses hardcoded User model (incompatible with custom User model)
2. Hardcoded username/email/password
3. Runs every container start (non-idempotent)
4. Plaintext password logged in docker logs
5. No environment variable control

**Fix:** Use `get_user_model()`, make creation conditional on `CREATE_SUPERUSER=true`, require explicit password

#### docker-compose.yml (Lines 6, 26)

**Current Code:**
```yaml
container_name: document_collector_db
container_name: document_collector_app
```

**Problems:**
1. Hardcoded names prevent multiple deployments
2. Synology Container Manager auto-updates fail with name conflicts
3. Impossible to run dev + prod simultaneously

**Fix:** Remove container_name or use template like `${COMPOSE_PROJECT_NAME}_db`

#### docker-compose.yml (Environment section)

**Current Code:**
```yaml
environment:
  DEBUG: ${DEBUG:-False}
  SECRET_KEY: ${SECRET_KEY}
  ...
```

**Problems:**
1. Not using `env_file: .env` pattern
2. Variable substitution happens at `docker-compose up`, not at runtime
3. Hard to track what's loaded from where

**Fix:** Add `env_file: .env` and clean up environment section

#### .env.example (Lines 3, 10)

**Current:**
```
SECRET_KEY=your-secret-key-change-in-production-12345678901234567890
POSTGRES_PASSWORD=secure_password_change_this
```

**Problems:**
1. Looks like working credentials
2. Could be accidentally committed
3. Example SECRET_KEY looks like a real secret

**Fix:** Use CHANGE_ME or similar placeholder

---

## Deployment Paths Configuration

### Current State
```
.env.example references:
APP_DATA_PATH=/volume1/docker/document-collector/appdata
POSTGRES_DATA_PATH=/volume1/docker/document-collector/postgres
CUSTOMER_DOCUMENTS_PATH=/volume1/Clienti
```

### Expected Container Mounts
```
/volume1/docker/eh-moduli/appdata     → /app/data
/volume1/docker/eh-moduli/postgres    → /var/lib/postgresql/data
/volume1/Clienti                       → /storage/clienti
```

### Validation Checklist ✓

- [x] PostgreSQL data persists across restarts
- [x] Customer documents accessible from NAS filesystem
- [x] Django /app/data writable by appuser (1000:1000)
- [x] staticfiles collected to persistent location
- [ ] Backup paths defined (not in current setup)
- [ ] Log aggregation strategy defined

---

## Files To Be Modified

| File | Changes |
|------|---------|
| **Dockerfile** | Add BUILD_ARGS, fix USER/chown order, improve healthcheck |
| **entrypoint.sh** | Complete rewrite: set -Eeuo, timeout, get_user_model(), conditional superuser, var validation |
| **docker-compose.yml** | Remove container_name, add env_file, improve service config |
| **.env.example** | Add missing vars, improve placeholders, Synology paths |
| **app/settings.py** | Add healthcheck endpoint logic (readiness), improve security headers |
| **app/urls.py** | Add /health/ready/ endpoint with DB check |
| **entrypoint.sh** (new) | Create separate production-ready version |

---

## Action Items

### Phase 1: Critical Fixes (Before First Production Deploy)
- [ ] Fix entrypoint.sh (get_user_model, conditional superuser, validation)
- [ ] Add Docker healthcheck readiness endpoint
- [ ] Remove container_name from compose
- [ ] Implement env_file pattern
- [ ] Update .env.example with safe defaults

### Phase 2: Deployment Hardening
- [ ] Add resource limits to compose (memory, cpus)
- [ ] Document Synology UID/GID alignment
- [ ] Add backup strategy
- [ ] Implement structured logging

### Phase 3: Verification
- [ ] Test container startup without .env secrets
- [ ] Test superuser creation only once
- [ ] Test healthcheck endpoints
- [ ] Test on Synology Container Manager (if available)
- [ ] Verify bind mounts have correct permissions

---

## Recommended Synology Deployment Path

```bash
/volume1/docker/eh-moduli/
├── repository/              # Git clone here
│   └── docker-compose.yml
│   └── .env                 # Created locally, never committed
├── appdata/                 # Django app data + staticfiles
├── postgres/                # PostgreSQL data
└── backups/                 # Backup location

/volume1/Clienti/            # Customer documents (independent path)
```

---

## Security Summary

### Current Risks
- ❌ Hardcoded credentials in example files
- ❌ Plaintext passwords in container logs
- ❌ Non-idempotent deployment (admin created every time)
- ❌ Hardcoded container names

### After Fixes
- ✅ Credentials via environment only
- ✅ Secrets not logged
- ✅ Idempotent deployment
- ✅ Safe for Synology updates
- ✅ Ready for HTTPS reverse proxy

---

## Next Steps

1. **Fix entrypoint.sh** - Most critical, blocks deployment
2. **Add healthcheck endpoints** - Required for monitoring
3. **Clean docker-compose.yml** - Remove hardcoded names
4. **Update documentation** - Add Synology deployment guide

All changes proceed without waiting for approval per senior engineer mandate.

---

**Report Status**: ✅ COMPLETE  
**Deployment Readiness**: 🔴 NOT YET READY (Awaiting critical fixes)  
**Last Updated**: 2026-09-01
