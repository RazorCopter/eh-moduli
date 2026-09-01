# Quick Start - Production Deployment

**For Synology NAS - 15 Minutes**

---

## Prerequisites

- Synology NAS with Docker installed
- SSH access
- NAS IP address (example: `192.168.1.100`)

---

## Step 1: SSH into NAS

```bash
ssh admin@192.168.1.100
# Enter password when prompted
```

---

## Step 2: Clone Repository

```bash
# Create directory
mkdir -p /volume1/docker/eh-moduli/repository
cd /volume1/docker/eh-moduli/repository

# Clone
git clone https://github.com/RazorCopter/eh-moduli.git .

# Verify files exist
ls -la Dockerfile docker-compose.yml .env.example
```

---

## Step 3: Create Directories

```bash
# Create all required directories
mkdir -p /volume1/docker/eh-moduli/{appdata,postgres,backups}
mkdir -p /volume1/Clienti

# Set permissions
chmod 755 /volume1/Clienti
chmod 755 /volume1/docker/eh-moduli
```

---

## Step 4: Generate Secrets

```bash
# Generate SECRET_KEY (copy output)
python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(50)))"

# Generate POSTGRES_PASSWORD (copy output)
openssl rand -base64 32
```

Keep these values handy.

---

## Step 5: Configure .env

```bash
cd /volume1/docker/eh-moduli/repository

# Copy template
cp .env.example .env

# Edit (use nano or vi)
nano .env
```

**Replace these values in .env:**

```bash
# Line 3 - Your SECRET_KEY from step 4
SECRET_KEY=paste_secret_key_here

# Line 10 - Your POSTGRES_PASSWORD from step 4
POSTGRES_PASSWORD=paste_password_here

# Line 23 - Your NAS IP
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100

# Line 27 - Your NAS IP
CSRF_TRUSTED_ORIGINS=http://localhost:6000,http://192.168.1.100:6000

# Line 47-49 - Set to true ONLY for first deployment
CREATE_SUPERUSER=true
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.local
DJANGO_SUPERUSER_PASSWORD=your_admin_password_here
```

**Save**: Ctrl+X → Y → Enter

---

## Step 6: Build and Start

```bash
cd /volume1/docker/eh-moduli/repository

# Build image (5-10 minutes, first time only)
docker-compose build

# Start containers
docker-compose up -d

# Watch startup logs (wait 30 seconds)
docker-compose logs -f app

# Exit logs: Ctrl+C
```

**Success signs in logs:**
- `[INFO] ✓ All startup checks completed successfully`
- `[INFO] Starting Gunicorn with 3 workers...`

---

## Step 7: Verify It Works

```bash
# Check containers running
docker-compose ps

# Test application
curl http://192.168.1.100:6000/

# Test admin login
curl http://192.168.1.100:6000/admin/

# Test health endpoints
curl http://192.168.1.100:6000/health/
curl http://192.168.1.100:6000/health/ready/
```

---

## Step 8: Access Application

Open browser to:

```
http://192.168.1.100:6000
```

Login:
- **URL**: http://192.168.1.100:6000/admin/
- **Username**: admin
- **Password**: (the one you set in step 5)

---

## Step 9: Disable Auto-Create Superuser

```bash
cd /volume1/docker/eh-moduli/repository

# Edit .env
nano .env

# Change this line:
CREATE_SUPERUSER=true
# To:
CREATE_SUPERUSER=false

# Save: Ctrl+X → Y → Enter

# Restart
docker-compose restart app
```

---

## Done! ✅

Your EHModuli instance is running on `http://NAS_IP:6000`

---

## Quick Commands Reference

```bash
cd /volume1/docker/eh-moduli/repository

# View logs
docker-compose logs -f app

# Stop containers
docker-compose stop

# Start containers
docker-compose start

# Restart containers
docker-compose restart app

# View health status
curl http://NAS_IP:6000/health/ready/

# Stop and remove (keeps data)
docker-compose down
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Connection refused` | Wait 60 seconds, then try again. Check `docker-compose logs app` |
| `Database error` | Check `docker-compose logs db`. Verify POSTGRES_PASSWORD in .env |
| `Permission denied` | Run `chmod 755 /volume1/docker/eh-moduli` |
| `Port 6000 in use` | Change APP_PORT in .env to 6001, rebuild with `docker-compose build` |

---

## Next: Full Documentation

For detailed information, see:
- `DEPLOYMENT_GUIDE.md` - Complete deployment guide
- `DEPLOYMENT_REVIEW.md` - What was fixed and why
- `CHANGELOG_DEPLOYMENT_FIXES.md` - All changes made

---

**Status**: ✅ PRODUCTION READY
