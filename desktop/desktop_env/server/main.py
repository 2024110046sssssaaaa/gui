"""
main.py - Entry point for the Linux server (backward compatibility wrapper).

For Linux VMs, this simply imports and runs main_linux.py.
For new deployments, prefer running main_linux.py directly.
"""

# Backward compatibility: delegate to main_linux.py
from main_linux import app

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
