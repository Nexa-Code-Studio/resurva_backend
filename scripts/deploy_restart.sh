#!/bin/bash
# Restart backend service
# Since this script is run with sudo, it executes as root.

echo "=== Restarting Backend Service (resurva_backend) ==="
systemctl restart resurva_backend
systemctl is-active resurva_backend
