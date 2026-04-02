# -----------------------------------------------------------------------------
# DOF-MESH SOVEREIGN CITADEL (PHASE 4.3) - Air-Gap Container
# -----------------------------------------------------------------------------
# Base Image: Python 3.13 (Slim) to match the host macOS environment closely
FROM python:3.13-slim

# Set environment variables for non-interactive installs and Python optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    NODE_VERSION=20.x

# Install System Dependencies, Build Tools, and Node.js (for Context7 MCP)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION} | bash - \
    && apt-get install -y nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set Working Directory (This will be bind-mounted from macOS)
WORKDIR /app

# Install Python requirements
# We copy only the requirements first to cache the pip install layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt || echo "Warning: Some requirements failed. Consider updating requirements.txt"

# Default Command: keeps the container alive for execution via mesh_run.sh
CMD ["tail", "-f", "/dev/null"]
