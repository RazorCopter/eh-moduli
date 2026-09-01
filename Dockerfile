FROM python:3.11-slim

# Build arguments for user customization (especially for Synology UID alignment)
ARG APPUSER_UID=1000
ARG APPUSER_GID=1000

# Set working directory
WORKDIR /app

# Install system dependencies with minimal bloat
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint executable before changing user
RUN chmod +x entrypoint.sh

# Create non-root user with custom UID/GID (important for Synology bind mounts)
# Group creation must come before user creation
RUN if ! getent group ${APPUSER_GID} >/dev/null; then \
        groupadd -g ${APPUSER_GID} appuser; \
    fi && \
    useradd -m -u ${APPUSER_UID} -g ${APPUSER_GID} appuser

# Create and set permissions on necessary directories
# These will be overridden by bind mounts, but need to exist with correct permissions
RUN mkdir -p /app/data /app/staticfiles /storage/clienti && \
    chown -R ${APPUSER_UID}:${APPUSER_GID} /app

# Switch to non-root user
USER appuser

# Expose port 8000 (container internal port)
EXPOSE 8000

# Health check: verify application is responding
# This is a liveness check - just verifies process is alive
# Readiness check (DB + filesystem) is in the app itself
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Use entrypoint for initialization and startup
ENTRYPOINT ["./entrypoint.sh"]
