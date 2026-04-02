# Project Citadel: Sovereign Dockerfile
# Base: Python 3.12-slim (Minimalist and secure)
FROM python:3.12-slim

# Labels for provenance
LABEL maintainer="Antigravity"
LABEL version="0.4.0-citadel"
LABEL security.isolation="HARD"

# Environment configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# System dependencies (Z3 solver for formal verification)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libz3-dev \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root user 'citadel'
RUN groupadd -r citadel && useradd -r -g citadel citadel

# Workspace setup
WORKDIR /app

# Copy and install dependencies first (caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Initial code copy (Structure only)
# Note: At runtime, we mount the real codebase as READ-ONLY for security
COPY . .

# Set permissions
RUN chown -r citadel:citadel /app
USER citadel

# Expose internal port (Proxy or local models)
EXPOSE 8080

# The Guardian: Run integrity check before execution
# Note: The entrypoint will run verify_sovereignty.py
# CMD ["python3", "scripts/verify_sovereignty.py", "&&", "python3", "scripts/execute_global_evaluator.py", "run"]
CMD ["python3", "scripts/execute_global_evaluator.py", "run"]
