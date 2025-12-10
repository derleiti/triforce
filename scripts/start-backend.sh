#!/bin/bash
# AILinux Backend Start Script
# Handles initialization and startup of the main backend service

set -e

# Configuration
BASE_DIR="/home/zombie/ailinux-ai-server-backend"
VENV_DIR="$BASE_DIR/.venv"
LOG_DIR="$BASE_DIR/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Activate Virtual Environment
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo "Error: Virtual environment not found at $VENV_DIR"
    exit 1
fi

# Set Environment Variables
export PYTHONPATH="$BASE_DIR"
export PYTHONUNBUFFERED=1

# Pre-flight Checks
# (Optional: Check Redis connection, etc. here if needed, 
#  but systemd 'Requires' usually handles service dependencies)

echo "Starting AILinux Backend..."
echo "Date: $(date)"

# Start Uvicorn
# Using exec to replace the shell process with uvicorn (better for signal handling)
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 9100 \
    --workers 4 \
    --log-level info \
    --no-access-log
