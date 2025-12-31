#!/bin/bash
# Deploy Mesh Guardian to all servers
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TRIFORCE_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== AILinux Mesh Guardian Deployment ==="

# 1. Commit and push latest
echo "[1/4] Syncing to GitHub..."
cd "$TRIFORCE_DIR"
git add -A
git commit -m "Guardian deployment $(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
git push origin master 2>/dev/null || echo "Push failed or nothing to push"

# 2. Deploy to Backup Server
echo "[2/4] Deploying to Backup Server..."
ssh backup "cd ~/triforce && git pull origin master" 2>/dev/null || {
    echo "Backup server: git pull failed, trying fresh clone..."
    ssh backup "rm -rf ~/triforce && git clone --depth 1 https://github.com/derleiti/ailinux-ai-server-backend.git ~/triforce"
}

# 3. Setup Guardian on Backup
echo "[3/4] Setting up Guardian on Backup..."
ssh backup << 'REMOTE'
cd ~/triforce

# Ensure venv exists
if [ ! -d .venv ]; then
    python3 -m venv .venv
    .venv/bin/pip install -q aiohttp websockets
fi

# Create log dir
mkdir -p logs
touch /tmp/mesh-guardian.log 2>/dev/null || true

# Fix paths in guardian for backupuser
sed -i 's|/home/zombie|/home/backupuser|g' scripts/mesh-guardian.py 2>/dev/null || true

# Test run
echo "Testing guardian..."
timeout 5 .venv/bin/python scripts/mesh-guardian.py --once 2>&1 || echo "Test complete"
REMOTE

# 4. Start Guardian on both servers
echo "[4/4] Starting Guardians..."

# Local (Hetzner)
echo "Starting local guardian..."
pkill -f "mesh-guardian.py" 2>/dev/null || true
nohup "$TRIFORCE_DIR/.venv/bin/python" "$TRIFORCE_DIR/scripts/mesh-guardian.py" --interval 30 > /tmp/mesh-guardian.log 2>&1 &
sleep 2

# Remote (Backup)
echo "Starting remote guardian..."
ssh backup "pkill -f mesh-guardian.py 2>/dev/null || true; cd ~/triforce && nohup .venv/bin/python scripts/mesh-guardian.py --interval 30 > /tmp/mesh-guardian.log 2>&1 &"

echo ""
echo "=== Deployment Complete ==="
echo "Hetzner Guardian: tail -f /tmp/mesh-guardian.log"
echo "Backup Guardian:  ssh backup 'tail -f /tmp/mesh-guardian.log'"
