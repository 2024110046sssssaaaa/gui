"""
common.py - Shared Flask routes and utilities used by all platform servers.

This file contains NO platform-specific imports. All platform-specific logic
is delegated to the individual main_<platform>.py files.
"""

import concurrent.futures
import ctypes
import json
import logging
import os
import platform
import re
import shlex
import signal
import subprocess
from pathlib import Path
from typing import Any, List, Optional, Set

from flask import Flask, request, jsonify, send_file, abort

# Global Flask app (must be defined before @app.route decorators)
app = Flask(__name__)

# Logging
logger = logging.getLogger("desktopenv.server.common")
logger.setLevel(logging.INFO)

# Global state
recording_process = None
recording_path = "/tmp/recording.mp4"


# ============================================================
# Accessibiltiy namespace maps (shared across platforms)
# ============================================================
_accessibility_ns_map = {
    "ubuntu": {
        "st": "https://accessibility.ubuntu.example.org/ns/state",
        "attr": "https://accessibility.ubuntu.example.org/ns/attributes",
        "cp": "https://accessibility.ubuntu.example.org/ns/component",
        "doc": "https://accessibility.ubuntu.example.org/ns/document",
        "docattr": "https://accessibility.ubuntu.example.org/ns/document/attributes",
        "txt": "https://accessibility.ubuntu.example.org/ns/text",
        "val": "https://accessibility.ubuntu.example.org/ns/value",
        "act": "https://accessibility.ubuntu.example.org/ns/action",
    },
    "windows": {
        "st": "https://accessibility.windows.example.org/ns/state",
        "attr": "https://accessibility.windows.example.org/ns/attributes",
        "cp": "https://accessibility.windows.example.org/ns/component",
        "doc": "https://accessibility.windows.example.org/ns/document",
        "docattr": "https://accessibility.windows.example.org/ns/document/attributes",
        "txt": "https://accessibility.windows.example.org/ns/text",
        "val": "https://accessibility.windows.example.org/ns/value",
        "act": "https://accessibility.windows.example.org/ns/action",
        "class": "https://accessibility.windows.example.org/ns/class",
    },
    "macos": {
        "st": "https://accessibility.macos.example.org/ns/state",
        "attr": "https://accessibility.macos.example.org/ns/attributes",
        "cp": "https://accessibility.macos.example.org/ns/component",
        "doc": "https://accessibility.macos.example.org/ns/document",
        "txt": "https://accessibility.macos.example.org/ns/text",
        "val": "https://accessibility.macos.example.org/ns/value",
        "act": "https://accessibility.macos.example.org/ns/action",
        "role": "https://accessibility.macos.example.org/ns/role",
    }
}

_accessibility_ns_map_ubuntu = _accessibility_ns_map['ubuntu']
_accessibility_ns_map_windows = _accessibility_ns_map['windows']
_accessibility_ns_map_macos = _accessibility_ns_map['macos']

MAX_DEPTH = 50
MAX_WIDTH = 1024
MAX_CALLS = 5000


# ============================================================
# Architecture helper (shared)
# ============================================================
def _get_machine_architecture() -> str:
    architecture = platform.machine().lower()
    if architecture in ['amd32', 'amd64', 'x86', 'x86_64', 'x86-64', 'x64', 'i386', 'i686']:
        return 'amd'
    elif architecture in ['arm64', 'aarch64', 'aarch32']:
        return 'arm'
    else:
        return 'unknown'


# ============================================================
# Common: execute command (works on all platforms)
# ============================================================
@app.route('/setup/execute', methods=['POST'])
@app.route('/execute', methods=['POST'])
def execute_command():
    data = request.json
    shell = data.get('shell', False)
    command = data.get('command', "" if shell else [])

    if isinstance(command, str) and not shell:
        command = shlex.split(command)

    for i, arg in enumerate(command):
        if arg.startswith("~/"):
            command[i] = os.path.expanduser(arg)

    try:
        if platform.system() == "Windows":
            flags = subprocess.CREATE_NO_WINDOW
        else:
            flags = 0
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            text=True,
            timeout=120,
            creationflags=flags,
        )
        return jsonify({
            'status': 'success',
            'output': result.stdout,
            'error': result.stderr,
            'returncode': result.returncode
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# ============================================================
# Common: launch app (works on all platforms)
# ============================================================
@app.route('/setup/launch', methods=["POST"])
def launch_app():
    data = request.json
    shell = data.get("shell", False)
    command: List[str] = data.get("command", "" if shell else [])

    if isinstance(command, str) and not shell:
        command = shlex.split(command)

    for i, arg in enumerate(command):
        if arg.startswith("~/"):
            command[i] = os.path.expanduser(arg)

    try:
        if 'google-chrome' in command and _get_machine_architecture() == 'arm':
            idx = command.index('google-chrome')
            command[idx] = 'chromium'
        subprocess.Popen(command, shell=shell)
        return "{:} launched successfully".format(command if shell else " ".join(command))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================
# Common: screenshot (platform-specific implementation in each main_*.py)
# NOTE: The route is NOT defined here. Each platform's main_*.py must
# define /screenshot and use its own _screenshot_linux implementation.
# This avoids a Python closure issue where the route would capture
# common._screenshot_linux (a stub) instead of the real implementation.
# ============================================================


# ============================================================
# Common: directory tree
# ============================================================
@app.route('/list_directory', methods=['POST'])
def get_directory_tree():
    def _list_dir_contents(directory):
        tree = {'type': 'directory', 'name': os.path.basename(directory), 'children': []}
        try:
            for entry in os.listdir(directory):
                full_path = os.path.join(directory, entry)
                if os.path.isdir(full_path):
                    tree['children'].append(_list_dir_contents(full_path))
                else:
                    tree['children'].append({'type': 'file', 'name': entry})
        except OSError as e:
            tree = {'error': str(e)}
        return tree

    data = request.get_json()
    if 'path' not in data:
        return jsonify(error="Missing 'path' parameter"), 400

    start_path = data['path']
    if not os.path.isdir(start_path):
        return jsonify(error="The provided path is not a directory"), 400

    directory_tree = _list_dir_contents(start_path)
    return jsonify(directory_tree=directory_tree)


# ============================================================
# Common: get file
# ============================================================
@app.route('/file', methods=['POST'])
def get_file():
    if 'file_path' in request.form:
        file_path = os.path.expandvars(os.path.expanduser(request.form['file_path']))
    else:
        return jsonify({"error": "file_path is required"}), 400

    try:
        return send_file(file_path, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404


# ============================================================
# Common: upload file
# ============================================================
@app.route("/setup/upload", methods=["POST"])
def upload_file():
    if 'file_path' in request.form and 'file_data' in request.files:
        file_path = os.path.expandvars(os.path.expanduser(request.form['file_path']))
        file = request.files["file_data"]
        file.save(file_path)
        return "File Uploaded"
    else:
        return jsonify({"error": "file_path and file_data are required"}), 400


# ============================================================
# Common: download file
# ============================================================
@app.route("/setup/download_file", methods=['POST'])
def download_file():
    data = request.json
    url = data.get('url', None)
    path = data.get('path', None)

    if not url or not path:
        return "Path or URL not supplied!", 400

    path = Path(os.path.expandvars(os.path.expanduser(path)))
    path.parent.mkdir(parents=True, exist_ok=True)

    max_retries = 3
    error: Optional[Exception] = None
    for i in range(max_retries):
        try:
            import requests
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            return "File downloaded successfully"
        except requests.RequestException as e:
            error = e
            logger.error(f"Failed to download {url}. Retrying... ({max_retries - i - 1} attempts left)")

    return f"Failed to download {url}. No retries left. Error: {error}", 500


# ============================================================
# Common: open file
# ============================================================
@app.route("/setup/open_file", methods=['POST'])
def open_file():
    data = request.json
    path = data.get('path', None)

    if not path:
        return "Path not supplied!", 400

    path = Path(os.path.expandvars(os.path.expanduser(path)))

    if not path.exists():
        return f"File not found: {path}", 404

    try:
        if platform.system() == "Windows":
            os.startfile(path)
        else:
            open_cmd = "open" if platform.system() == "Darwin" else "xdg-open"
            subprocess.Popen([open_cmd, str(path)])
        return "File opened successfully"
    except Exception as e:
        return f"Failed to open {path}. Error: {e}", 500


# ============================================================
# Common: get platform
# ============================================================
@app.route('/platform', methods=['GET'])
def get_platform():
    return platform.system()


# ============================================================
# Common: cursor position
# ============================================================
@app.route('/cursor_position', methods=['GET'])
def get_cursor_position():
    import pyautogui
    pos = pyautogui.position()
    return jsonify(pos.x, pos.y)


# ============================================================
# Common: wallpaper (platform-specific helpers)
# ============================================================
@app.route("/setup/change_wallpaper", methods=['POST'])
def change_wallpaper():
    data = request.json
    path = data.get('path', None)

    if not path:
        return "Path not supplied!", 400

    path = Path(os.path.expandvars(os.path.expanduser(path)))

    if not path.exists():
        return f"File not found: {path}", 404

    try:
        os_name = platform.system()
        if os_name == "Windows":
            _change_wallpaper_windows(path)
        elif os_name == "Linux":
            _change_wallpaper_linux(path)
        elif os_name == "Darwin":
            _change_wallpaper_darwin(path)
        return "Wallpaper changed successfully"
    except Exception as e:
        return f"Failed to change wallpaper. Error: {e}", 500


@app.route('/wallpaper', methods=['POST'])
def get_wallpaper():
    def _get_wallpaper_windows():
        SPI_GETDESKWALLPAPER = 0x73
        MAX_PATH = 260
        buffer = ctypes.create_unicode_buffer(MAX_PATH)
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETDESKWALLPAPER, MAX_PATH, buffer, 0)
        return buffer.value

    def _get_wallpaper_macos():
        script = "tell application \"System Events\" to tell every desktop to get picture"
        process = subprocess.Popen(['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        if error:
            app.logger.error("Error: %s", error.decode('utf-8'))
            return None
        return output.strip().decode('utf-8')

    def _get_wallpaper_linux():
        try:
            output = subprocess.check_output(
                ["gsettings", "get", "org.gnome.desktop.background", "picture-uri"],
                stderr=subprocess.PIPE
            )
            return output.decode('utf-8').strip().replace('file://', '').replace("'", "")
        except subprocess.CalledProcessError as e:
            app.logger.error("Error: %s", e)
            return None

    os_name = platform.system()
    wallpaper_path = None
    if os_name == 'Windows':
        wallpaper_path = _get_wallpaper_windows()
    elif os_name == 'Darwin':
        wallpaper_path = _get_wallpaper_macos()
    elif os_name == 'Linux':
        wallpaper_path = _get_wallpaper_linux()
    else:
        app.logger.error(f"Unsupported OS: {os_name}")
        abort(400, description="Unsupported OS")

    if wallpaper_path:
        try:
            return send_file(wallpaper_path, mimetype='image/png')
        except Exception as e:
            app.logger.error(f"An error occurred while serving the wallpaper file: {e}")
            abort(500, description="Unable to serve the wallpaper file")
    else:
        abort(404, description="Wallpaper file not found")


# ============================================================
# Common: activate / close window (platform-specific)
# ============================================================
@app.route("/setup/activate_window", methods=['POST'])
def activate_window():
    data = request.json
    window_name = data.get('window_name', None)
    if not window_name:
        return "window_name required", 400
    strict: bool = data.get("strict", False)
    by_class_name: bool = data.get("by_class", False)

    os_name = platform.system()

    if os_name == 'Windows':
        return _activate_window_windows(window_name, strict)
    elif os_name == 'Darwin':
        return _activate_window_darwin(window_name, strict)
    elif os_name == 'Linux':
        return _activate_window_linux(window_name, strict, by_class_name)
    else:
        return f"Operating system {os_name} not supported.", 400


@app.route("/setup/close_window", methods=["POST"])
def close_window():
    data = request.json
    if "window_name" not in data:
        return "window_name required", 400
    window_name: str = data["window_name"]
    strict: bool = data.get("strict", False)
    by_class_name: bool = data.get("by_class", False)

    os_name = platform.system()
    if os_name == "Windows":
        return _close_window_windows(window_name, strict)
    elif os_name == "Linux":
        return _close_window_linux(window_name, strict, by_class_name)
    elif os_name == "Darwin":
        return _close_window_darwin(window_name)
    else:
        return "Not supported platform {:}".format(os_name), 500


# ============================================================
# Common: desktop path
# ============================================================
@app.route('/desktop_path', methods=['POST'])
def get_desktop_path():
    home_directory = str(Path.home())
    desktop_path = {
        "Windows": os.path.join(home_directory, "Desktop"),
        "Darwin": os.path.join(home_directory, "Desktop"),
        "Linux": os.path.join(home_directory, "Desktop")
    }.get(platform.system(), None)

    if desktop_path and os.path.exists(desktop_path):
        return jsonify(desktop_path=desktop_path)
    else:
        return jsonify(error="Unsupported operating system or desktop path not found"), 404


# ============================================================
# The following MUST be overridden in each platform's main_*.py:
#   _screenshot_windows / _screenshot_linux / _screenshot_darwin
#   get_accessibility_tree
#   get_screen_size
#   get_window_size
#   get_terminal_output
#   start_recording / end_recording
#   _change_wallpaper_windows / _change_wallpaper_linux / _change_wallpaper_darwin
#   _activate_window_windows / _activate_window_linux / _activate_window_darwin
#   _close_window_windows / _close_window_linux / _close_window_darwin
# ============================================================

def _screenshot_windows(file_path):
    raise NotImplementedError("Implement in main_windows.py")


def _screenshot_linux(file_path):
    raise NotImplementedError("Implement in main_linux.py")


def _screenshot_darwin(file_path):
    raise NotImplementedError("Implement in main_darwin.py")


def _change_wallpaper_windows(path):
    raise NotImplementedError("Implement in main_windows.py")


def _change_wallpaper_linux(path):
    raise NotImplementedError("Implement in main_linux.py")


def _change_wallpaper_darwin(path):
    raise NotImplementedError("Implement in main_darwin.py")


def _activate_window_windows(window_name, strict):
    raise NotImplementedError("Implement in main_windows.py")


def _activate_window_darwin(window_name, strict):
    raise NotImplementedError("Implement in main_darwin.py")


def _activate_window_linux(window_name, strict, by_class_name):
    raise NotImplementedError("Implement in main_linux.py")


def _close_window_windows(window_name, strict):
    raise NotImplementedError("Implement in main_windows.py")


def _close_window_darwin(window_name):
    raise NotImplementedError("Implement in main_darwin.py")


def _close_window_linux(window_name, strict, by_class_name):
    raise NotImplementedError("Implement in main_linux.py")
