#!/usr/bin/env bash
# Deploy the GHL webhook receiver as a systemd service.
set -euo pipefail

INSTALL_DIR="/home/keith/real_estate/4plex-investment-platform"
SERVICE_NAME="ghl-webhook"

echo "==> Linking systemd service..."
sudo cp "${INSTALL_DIR}/scripts/systemd/${SERVICE_NAME}.service" /etc/systemd/system/
sudo systemctl daemon-reload

echo "==> Enabling the service to start on boot..."
sudo systemctl enable "${SERVICE_NAME}"

echo "==> Starting the service..."
sudo systemctl restart "${SERVICE_NAME}"

echo "==> Checking status..."
sleep 2
sudo systemctl status "${SERVICE_NAME}" --no-pager

echo ""
echo "==> Done.  Check logs with:  sudo journalctl -fu ${SERVICE_NAME}"
