#!/bin/bash
set -Eeuo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration from environment
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-document_collector}"
POSTGRES_USER="${POSTGRES_USER:-collector_user}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT:-90}"
CREATE_SUPERUSER="${CREATE_SUPERUSER:-false}"
DJANGO_SUPERUSER_USERNAME="${DJANGO_SUPERUSER_USERNAME:-}"
DJANGO_SUPERUSER_EMAIL="${DJANGO_SUPERUSER_EMAIL:-}"
DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-60}"
GUNICORN_LOG_LEVEL="${GUNICORN_LOG_LEVEL:-info}"

# Utility functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Validate required environment variables
validate_env_vars() {
    log_info "Validating environment variables..."

    local required_vars=(
        "POSTGRES_HOST"
        "POSTGRES_DB"
        "POSTGRES_USER"
        "POSTGRES_PORT"
    )

    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            log_error "Required environment variable not set: $var"
            exit 1
        fi
    done

    if [ -z "${POSTGRES_PASSWORD:-}" ]; then
        log_error "POSTGRES_PASSWORD must be set"
        exit 1
    fi

    if [ -z "${SECRET_KEY:-}" ]; then
        log_error "SECRET_KEY must be set"
        exit 1
    fi

    log_info "✓ All required environment variables are set"
}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    log_info "Waiting for PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT (timeout: ${DB_WAIT_TIMEOUT}s)..."

    local start_time=$(date +%s)
    local end_time=$((start_time + DB_WAIT_TIMEOUT))

    while true; do
        current_time=$(date +%s)

        if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
            log_info "✓ PostgreSQL is ready"
            return 0
        fi

        if [ $current_time -ge $end_time ]; then
            log_error "PostgreSQL did not become ready within ${DB_WAIT_TIMEOUT} seconds"
            exit 1
        fi

        sleep 2
    done
}

# Verify storage directories are writable
verify_storage() {
    log_info "Verifying storage directories..."

    # Check /app/data
    if [ ! -d "/app/data" ]; then
        log_warn "/app/data does not exist, creating it..."
        mkdir -p /app/data || {
            log_error "Failed to create /app/data"
            exit 1
        }
    fi

    if [ ! -w "/app/data" ]; then
        log_error "/app/data is not writable by current user"
        exit 1
    fi
    log_info "✓ /app/data is writable"

    # Check /storage/clienti
    if [ ! -d "/storage/clienti" ]; then
        log_warn "/storage/clienti does not exist, creating it..."
        mkdir -p /storage/clienti || {
            log_error "Failed to create /storage/clienti"
            exit 1
        }
    fi

    if [ ! -w "/storage/clienti" ]; then
        log_error "/storage/clienti is not writable by current user"
        exit 1
    fi
    log_info "✓ /storage/clienti is writable"

    # Test write access with temp file
    local test_file="/storage/clienti/.healthcheck_$(date +%s)"
    if ! touch "$test_file" 2>/dev/null; then
        log_error "Cannot write to /storage/clienti (permission denied)"
        exit 1
    fi
    rm -f "$test_file"
    log_info "✓ /storage/clienti write test passed"
}

# Run Django migrations
run_migrations() {
    log_info "Running Django migrations..."

    if ! python manage.py migrate --noinput; then
        log_error "Migrations failed"
        exit 1
    fi

    log_info "✓ Migrations completed successfully"
}

# Collect static files
collect_static() {
    log_info "Collecting static files..."

    if ! python manage.py collectstatic --noinput --clear; then
        log_error "Static files collection failed"
        exit 1
    fi

    log_info "✓ Static files collected successfully"
}

# Create superuser if requested
create_superuser() {
    if [ "$CREATE_SUPERUSER" != "true" ]; then
        log_info "Superuser creation disabled (CREATE_SUPERUSER != true)"
        return 0
    fi

    log_info "Checking superuser creation requirements..."

    if [ -z "$DJANGO_SUPERUSER_USERNAME" ]; then
        log_warn "DJANGO_SUPERUSER_USERNAME not set, skipping superuser creation"
        return 0
    fi

    if [ -z "$DJANGO_SUPERUSER_EMAIL" ]; then
        log_warn "DJANGO_SUPERUSER_EMAIL not set, skipping superuser creation"
        return 0
    fi

    if [ -z "$DJANGO_SUPERUSER_PASSWORD" ]; then
        log_warn "DJANGO_SUPERUSER_PASSWORD not set, skipping superuser creation"
        return 0
    fi

    log_info "Creating superuser: $DJANGO_SUPERUSER_USERNAME"

    # Use Django's shell to safely create superuser with custom User model
    python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()

username = "$DJANGO_SUPERUSER_USERNAME"
email = "$DJANGO_SUPERUSER_EMAIL"

if User.objects.filter(username=username).exists():
    print(f"[INFO] Superuser '{username}' already exists")
else:
    User.objects.create_superuser(username, email, "$DJANGO_SUPERUSER_PASSWORD")
    print(f"[INFO] Superuser '{username}' created successfully")
EOF

    if [ $? -eq 0 ]; then
        log_info "✓ Superuser handling completed"
    else
        log_error "Failed to create superuser"
        exit 1
    fi
}

# Health check endpoint test
test_healthcheck() {
    log_info "Testing Django application startup..."

    if ! timeout 10 python manage.py check > /dev/null 2>&1; then
        log_error "Django application check failed"
        exit 1
    fi

    log_info "✓ Django application is healthy"
}

# Main execution
main() {
    log_info "=========================================="
    log_info "EHModuli Container Entrypoint"
    log_info "=========================================="
    log_info "Environment: ${ENVIRONMENT:-development}"
    log_info "Workers: $GUNICORN_WORKERS"
    log_info "Timeout: $GUNICORN_TIMEOUT"
    log_info "=========================================="

    validate_env_vars
    wait_for_postgres
    verify_storage
    run_migrations
    collect_static
    create_superuser
    test_healthcheck

    log_info "=========================================="
    log_info "✓ All startup checks completed successfully"
    log_info "Starting Gunicorn with $GUNICORN_WORKERS workers..."
    log_info "=========================================="

    exec gunicorn \
        app.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers "$GUNICORN_WORKERS" \
        --worker-class sync \
        --worker-tmp-dir /dev/shm \
        --timeout "$GUNICORN_TIMEOUT" \
        --log-level "$GUNICORN_LOG_LEVEL" \
        --access-logfile - \
        --error-logfile -
}

main "$@"
