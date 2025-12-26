#!/usr/bin/env bash
set -euo pipefail

# Usage: sudo ./systemd-install.sh /home/ubuntu/DevOps/docker
PROJECT_DIR=${1:-$(pwd)}
SERVICE_NAME=${2:-docker-stack.service}

if [ "$EUID" -ne 0 ]; then
  echo "This script requires sudo/root to copy files to /etc/systemd/system. Rerun with sudo."
  exit 2
fi

SRC_UNIT="$PROJECT_DIR/deploy/$SERVICE_NAME"
DEST_UNIT="/etc/systemd/system/$SERVICE_NAME"

if [ ! -f "$SRC_UNIT" ]; then
  echo "Unit file not found: $SRC_UNIT"
  exit 3
fi

cp "$SRC_UNIT" "$DEST_UNIT"
chmod 644 "$DEST_UNIT"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo "Installed and started $SERVICE_NAME. Check status with: systemctl status $SERVICE_NAME"
