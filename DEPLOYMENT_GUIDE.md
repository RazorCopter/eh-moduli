# EHModuli Deployment Guide - Synology NAS

**Version**: 1.0  
**Target**: Synology NAS with Docker or Container Manager  
**Database**: PostgreSQL 15  
**Last Updated**: 2026-09-01

---

## Prerequisites

- Synology NAS with Docker installed (or Container Manager)
- SSH access to NAS (optional but recommended)
- At least 5GB free space on /volume1
- NAS IP address or hostname known

---

## Step 1: Prepare Directory Structure on NAS

Create required directories on the NAS. Use SSH or SMB:

```bash
# SSH into NAS (replace with your NAS IP)
ssh admin@192.168.1.100

# Create directory structure
mkdir -p /volume1/docker/eh-moduli/{appdata,postgres,backups}
mkdir -p /volume1/Clienti

# Set proper permissions
chmod 755 /volume1/Clienti
chmod 755 /volume1/docker/eh-moduli

# Verify structure
ls -la /volume1/docker/eh-moduli/
ls -la /volume1/Clienti/
```

**Expected structure:**
```
/volume1/docker/eh-moduli/
├── appdata/                 # Django data, static files
├── postgres/                # PostgreSQL data
├── backups/                 # Backup location
└── repository/              # (Will contain docker-compose.yml, .env)

/volume1/Clienti/            # Customer documents
```

---

## Step 2: Clone or Upload Project Repository

### Option A: Clone with Git (Recommended)

Via SSH on the NAS:

```bash
mkdir -p /volume1/docker/eh-moduli/repository
cd /volume1/docker/eh-moduli/repository

# Clone the repository
git clone https://github.com/RazorCopter/eh-moduli.git .

# Verify files are present
ls -la
```

### Option B: Upload Files Manually

Upload all project files to `/volume1/docker/eh-moduli/repository` via SMB:
- Include `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`, all Python files
- Do NOT upload `.env` - it will be created in next step

---

## Step 3: Configure Environment Variables

Create `.env` file in repository directory:

```bash
# SSH into NAS
ssh admin@192.168.1.100
cd /volume1/docker/eh-moduli/repository

# Copy template
cp .env.example .env

# Edit with your values (using nano or vi)
nano .env
```

### Key Configuration Values

**Find your NAS IP:**
```bash
# On the NAS
hostname -I
# Example output: 192.168.1.100
```

### .env Values to Update

```bash
# Application
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=CHANGE_ME_TO_RANDOM_VALUE
APP_PORT=6060
TZ=Europe/Rome

# Generate SECRET_KEY on a Linux/Mac machine:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# Or use:
# openssl rand -base64 32

# Database
POSTGRES_DB=document_collector
POSTGRES_USER=collector_user
POSTGRES_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Generate POSTGRES_PASSWORD:
# openssl rand -base64 32

# Allowed hosts (CRITICAL - use your NAS IP or hostname)
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100
CSRF_TRUSTED_ORIGINS=http://localhost:6060,http://192.168.1.100:6060

# Storage paths (Synology)
APP_DATA_PATH=/volume1/docker/eh-moduli/appdata
POSTGRES_DATA_PATH=/volume1/docker/eh-moduli/postgres
CUSTOMER_DOCUMENTS_PATH=/volume1/Clienti

# First deployment ONLY:
CREATE_SUPERUSER=true
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.local
DJANGO_SUPERUSER_PASSWORD=CHANGE_ME_TO_SECURE_PASSWORD
```

**Save and exit**: Press Ctrl+X, then Y, then Enter (if using nano)

---

## Step 4: Verify .env File

Verify the .env file is correctly formatted:

```bash
# Check file exists
ls -la .env

# Verify no syntax errors
cat .env
```

**Important**: The .env file is NOT committed to Git (it's in .gitignore for security).

---

## Step 5: Build Docker Image

Build the Docker image for your NAS architecture:

```bash
# From /volume1/docker/eh-moduli/repository directory
docker-compose build

# This may take 5-10 minutes on first build
# Watch for errors during build
```

**Expected output:**
```
Building app
Step 1/X : FROM python:3.11-slim
...
Successfully built...
```

If build fails, check:
1. Docker daemon is running
2. Disk space available
3. Internet connection (for downloading dependencies)
4. .env file exists in repository directory

---

## Step 6: First Deployment - Create Database and Admin

Start the containers for the first time:

```bash
# From /volume1/docker/eh-moduli/repository directory
docker-compose up

# This will:
# 1. Start PostgreSQL
# 2. Run migrations
# 3. Create superuser
# 4. Start Django application
# 5. Show logs in terminal

# Watch for output like:
# [INFO] ✓ All startup checks completed successfully
# [INFO] Starting Gunicorn with 3 workers...
```

**Wait for:** "Starting Gunicorn..." message (usually 30-60 seconds)

**Stop with:** Ctrl+C

---

## Step 7: Run Containers in Background

Start containers in background (detached mode):

```bash
# From /volume1/docker/eh-moduli/repository directory
docker-compose up -d

# Verify containers are running
docker-compose ps

# Expected output:
# NAME                    STATUS
# eh-moduli_db_1          Up (healthy)
# eh-moduli_app_1         Up (healthy)

# View logs
docker-compose logs -f app

# Exit logs view: Ctrl+C
```

---

## Step 8: Disable Superuser Creation

After first successful deployment, disable automatic superuser creation:

```bash
# Edit .env file
nano .env

# Change this line:
CREATE_SUPERUSER=true
# To:
CREATE_SUPERUSER=false

# Save: Ctrl+X, Y, Enter
```

Then restart the container:

```bash
docker-compose restart app
```

---

## Step 9: Access Application

Open browser and navigate to:

```
http://192.168.1.100:6060
```

Replace `192.168.1.100` with your actual NAS IP.

### Admin Panel

Login with superuser credentials:
- URL: `http://192.168.1.100:6060/admin`
- Username: `admin` (or whatever you set)
- Password: (the password you configured)

---

## Step 10: Configure for HTTPS (Optional)

If you have a reverse proxy with SSL certificate:

Edit `.env`:

```bash
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://your-domain.com
```

Note: HTTPS reverse proxy must be configured on NAS or upstream firewall.

---

## Operational Tasks

### View Application Logs

```bash
# Real-time logs
docker-compose logs -f app

# Last 100 lines
docker-compose logs --tail=100 app

# Database logs
docker-compose logs -f db

# Exit: Ctrl+C
```

### Check Health Status

```bash
# Check container status
docker-compose ps

# Test liveness endpoint
curl http://192.168.1.100:6060/health/

# Test readiness endpoint (detailed)
curl http://192.168.1.100:6060/health/ready/

# Expected readiness output (if ready):
# {"status": "ready", "checks": {"database": true, "storage": true, "data_dir": true}}
```

### Stop Containers

```bash
# Stop but keep volumes
docker-compose stop

# Stop and remove containers (volumes persist)
docker-compose down

# Remove everything INCLUDING volumes (⚠️ DESTRUCTIVE)
docker-compose down -v
```

### Restart Containers

```bash
# Restart all services
docker-compose restart

# Restart only app
docker-compose restart app

# Restart only database
docker-compose restart db
```

### Update Container (New Version)

```bash
# Update code from git
cd /volume1/docker/eh-moduli/repository
git pull origin main

# Rebuild image (if Dockerfile changed)
docker-compose build

# Stop running containers
docker-compose stop

# Start updated version
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs -f app
```

### View Customer Documents

Customer documents are stored in:
```
/volume1/Clienti/
```

Access via SMB:
```
\\192.168.1.100\Clienti
```

Structure:
```
/volume1/Clienti/
├── customer_code_1/
│   └── assignment_id_1/
│       ├── requirement_1/
│       │   └── document.pdf
│       └── requirement_2/
└── customer_code_2/
```

### Backup Procedure

**PostgreSQL Data** (most important):
```bash
# SSH into NAS
ssh admin@192.168.1.100

# Backup database
docker exec eh-moduli_db_1 pg_dump -U collector_user document_collector > /volume1/docker/eh-moduli/backups/db_backup_$(date +%Y%m%d_%H%M%S).sql

# Or use automated backup (if you have cron)
# 0 2 * * * docker exec eh-moduli_db_1 pg_dump -U collector_user document_collector > /volume1/docker/eh-moduli/backups/db_backup_$(date +\%Y\%m\%d).sql
```

**Customer Documents**:
```bash
# Copy to backup location
cp -r /volume1/Clienti /volume1/docker/eh-moduli/backups/Clienti_$(date +%Y%m%d)
```

---

## Troubleshooting

### Containers Won't Start

**Check logs:**
```bash
docker-compose logs app
docker-compose logs db
```

**Common issues:**

| Issue | Solution |
|-------|----------|
| `POSTGRES_PASSWORD not set` | Edit .env, ensure `POSTGRES_PASSWORD` is set |
| `bind: permission denied` | Check port 6060 not in use: `docker ps` |
| `directory not writable` | Fix permissions: `chmod 755 /volume1/docker/eh-moduli` |
| `connection refused` | Wait longer for DB to start, check `docker-compose logs db` |

### Application Not Responding

```bash
# Check health
curl http://192.168.1.100:6060/health/ready/

# Check logs
docker-compose logs -f app

# Restart
docker-compose restart app

# If persistent, check disk space
df -h /volume1
```

### Database Connection Error

```bash
# Verify database is running
docker-compose logs db

# Check if pg_isready succeeds
docker-compose exec db pg_isready -U collector_user

# Restart database
docker-compose restart db
```

### Staticfiles Not Loading

```bash
# Collect static files manually
docker-compose exec app python manage.py collectstatic --noinput

# Check if directory exists
ls -la /volume1/docker/eh-moduli/appdata/staticfiles/
```

### Customer Can't Upload Documents

```bash
# Check /storage/clienti is writable
docker-compose exec app ls -la /storage/clienti

# Check permissions
docker-compose exec app touch /storage/clienti/.test && rm /storage/clienti/.test

# Check NAS storage space
df -h /volume1/Clienti
```

---

## Performance Tuning

For faster NAS with more resources, edit `.env`:

```bash
# Increase workers (NAS has 4+ CPU cores)
GUNICORN_WORKERS=5

# Reduce worker timeout if uploads are quick
GUNICORN_TIMEOUT=90

# Increase database connection timeout if NAS is slow
DB_WAIT_TIMEOUT=120
```

Then restart:
```bash
docker-compose restart app
```

---

## Security Checklist

Before going to production:

- [ ] `.env` file created and NOT committed to Git
- [ ] `SECRET_KEY` is a strong random value (not example)
- [ ] `POSTGRES_PASSWORD` is strong (20+ chars, mixed case, numbers, symbols)
- [ ] `DJANGO_SUPERUSER_PASSWORD` is strong
- [ ] `ALLOWED_HOSTS` includes your actual NAS IP or hostname
- [ ] `CREATE_SUPERUSER` is set to `false` after first deployment
- [ ] Application is accessible only on trusted network
- [ ] HTTPS reverse proxy is configured (if internet-facing)
- [ ] Regular backups are in place
- [ ] `/volume1/Clienti` permissions are restricted to NAS users

---

## Monitoring & Alerts

### Container Health Monitoring

Synology Container Manager shows:
- Container status (running/stopped)
- CPU/Memory usage
- Log output

Access via: **Container Manager → Containers → eh-moduli_app_1**

### Log Aggregation

Collect logs to external server (optional):

```bash
# Tail logs to file
docker-compose logs -f app >> /volume1/docker/eh-moduli/logs/app.log &
```

### Uptime Monitoring

External monitoring can use:
- `http://NAS_IP:6060/health/live/` - Liveness check
- `http://NAS_IP:6060/health/ready/` - Full readiness check

---

## Support & Troubleshooting Resources

1. **Application Logs**: `docker-compose logs app`
2. **Database Logs**: `docker-compose logs db`
3. **Container Status**: `docker-compose ps`
4. **Documentation**: See `README.md`, `ARCHITECTURE.md`
5. **Security**: See `SECURITY_TL_DR.md`

---

## Disaster Recovery

**If database is corrupted:**

```bash
# 1. Stop application
docker-compose stop app

# 2. Restore database from backup
docker-compose exec db psql -U collector_user document_collector < /volume1/docker/eh-moduli/backups/db_backup_latest.sql

# 3. Start application
docker-compose start app
```

**If customer documents are lost:**

```bash
# Restore from backup (if available)
cp -r /volume1/docker/eh-moduli/backups/Clienti_YYYYMMDD/* /volume1/Clienti/
```

---

## Version Upgrade Path

To upgrade to a newer version:

```bash
# 1. Backup current state
cp -r /volume1/Clienti /volume1/docker/eh-moduli/backups/Clienti_pre_upgrade
docker exec eh-moduli_db_1 pg_dump -U collector_user document_collector > /volume1/docker/eh-moduli/backups/db_pre_upgrade.sql

# 2. Pull latest code
cd /volume1/docker/eh-moduli/repository
git pull origin main

# 3. Rebuild and restart
docker-compose build
docker-compose up -d

# 4. Monitor logs
docker-compose logs -f app

# 5. Verify health
curl http://192.168.1.100:6060/health/ready/
```

---

**Status**: ✅ DEPLOYMENT READY  
**Last Tested**: September 2026  
**Support**: See repository issues on GitHub
