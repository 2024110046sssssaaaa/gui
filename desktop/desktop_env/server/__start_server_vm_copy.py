#!/usr/bin/env python3
"""
_start_server.py - Wrapper launcher for the OSWorld Flask server inside the VM.

This script is uploaded to /home/user/_start_server.py on the VM and acts as the
entry point. It sets up the required environment (DISPLAY, XAUTHORITY) and then
runs main_linux.py.

Usage:
    python3 _start_server.py

The parent shell or systemd service should set DISPLAY and XAUTHORITY, but this
wrapper also sets them as a safety net since environment variables can get lost
when nohup is used.
"""

import os
import sys
from pathlib import Path

# Force set DISPLAY and XAUTHORITY before any GUI-related imports.
# These MUST match what the GNOME session uses. User ID 1000 is standard on
# the Ubuntu VM image. The Xauthority path can vary by display manager, so we
# try common paths.
_display = (os.environ.get("DISPLAY") or ":0").strip() or ":0"

# Try to find a valid Xauthority file if the default doesn't exist
_xauth = os.environ.get("XAUTHORITY", "")
_default_xauth = "/run/user/1000/gdm/Xauthority"

if not _xauth or not os.path.exists(_xauth):
    candidates = [
        _default_xauth,
        "/home/user/.Xauthority",
        "/run/user/1000/Xauthority",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            _xauth = candidate
            break
    if not _xauth:
        fallback_xauth = "/home/user/.Xauthority"
        try:
            Path(fallback_xauth).touch(exist_ok=True)
            _xauth = fallback_xauth
        except Exception:
            _xauth = ""

os.environ["DISPLAY"] = _display
if _xauth and os.path.exists(_xauth):
    os.environ["XAUTHORITY"] = _xauth
else:
    os.environ.pop("XAUTHORITY", None)

# Ensure we're in the right directory
os.chdir("/home/user")

# Suppress pyautogui warnings
os.environ["PYAUTOGUI_WARNINGS"] = "0"

# Add /home/user to Python path so imports of common.py work
sys.path.insert(0, "/home/user")

if __name__ == "__main__":
    from main_linux import app
    # Run with threading=True because Flask's default (fork) breaks GUI apps on Linux
    # host="0.0.0.0" so the host machine can reach it
    # port=5000 matches what desktop_env.py expects
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False)
