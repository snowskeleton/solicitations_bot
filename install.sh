#!/bin/bash

# Install script for solicitations scraper systemd service

set -e

# Configuration
SERVICE_NAME="solicitations-scraper"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
WORKING_DIR="$(pwd)"
USER=$(whoami)

echo "Installing solicitations scraper systemd service..."

# Create systemd service file
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Solicitations Scraper
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORKING_DIR
Environment=PATH=$WORKING_DIR/venv/bin
ExecStart=$WORKING_DIR/venv/bin/gunicorn --bind 0.0.0.0:5002 main:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable "$SERVICE_NAME"

# Start the service
sudo systemctl start "$SERVICE_NAME"

echo "Service installed and started successfully!"
echo "Service status:"
sudo systemctl status "$SERVICE_NAME" --no-pager
