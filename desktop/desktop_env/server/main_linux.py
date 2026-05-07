"""
main_linux.py - OSWorld server for Linux (Ubuntu) VMs.

Run inside the Linux VM to provide screenshot, accessibility tree,
and desktop automation capabilities via HTTP endpoints.

Usage:
    python main_linux.py

Requires (pre-installed in the VM):
    pip install flask pyautogui lxml pillow requests pyxcursor pyatspi Xlib

The server listens on 0.0.0.0:5000 inside the VM. The host machine
communicates with it via PythonController (HTTP client).
"""

from __future__ import annotations

import logging
import os
import json
import platform
import shlex
import signal
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Normalize DISPLAY/XAUTHORITY before any GUI-related imports. The parent shell
# may pass DISPLAY with stray newlines, and the Xauthority path differs across
# GNOME/gdm/lightdm sessions.
os.environ["DISPLAY"] = (os.environ.get("DISPLAY") or ":0").strip() or ":0"
_xauthority = (os.environ.get("XAUTHORITY") or "").strip()
if not _xauthority or not os.path.exists(_xauthority):
    for _candidate in (
        "/run/user/1000/gdm/Xauthority",
        "/run/user/1000/Xauthority",
        "/home/user/.Xauthority",
    ):
        if os.path.exists(_candidate):
            _xauthority = _candidate
            break
    if not _xauthority:
        _fallback_xauthority = "/home/user/.Xauthority"
        try:
            Path(_fallback_xauthority).touch(exist_ok=True)
            _xauthority = _fallback_xauthority
        except Exception:
            _xauthority = ""
if _xauthority and os.path.exists(_xauthority):
    os.environ["XAUTHORITY"] = _xauthority
else:
    os.environ.pop("XAUTHORITY", None)

import pyautogui
import requests
from PIL import Image
from flask import Flask, jsonify, request, send_file

# Linux-specific imports
import pyatspi
from pyatspi import Accessible, StateType, STATE_SHOWING
from pyatspi import Action as ATAction
from pyatspi import Component
from pyatspi import Text as ATText
from pyatspi import Value as ATValue
import lxml.etree
from Xlib import display, X

from pyxcursor import Xcursor

# Import ALL shared routes from common.py
from common import (
    app,
    MAX_DEPTH,
    MAX_WIDTH,
    _accessibility_ns_map_ubuntu,
    _accessibility_ns_map_windows,
    _accessibility_ns_map_macos,
    _get_machine_architecture,
    execute_command,
    launch_app,
    get_directory_tree,
    get_file,
    upload_file,
    download_file,
    open_file,
    get_platform,
    get_cursor_position,
    change_wallpaper,
    get_wallpaper,
    activate_window,
    close_window,
    get_desktop_path,
    recording_process,
    recording_path,
)

# Re-export logger from the shared app
logger = app.logger

pyautogui.PAUSE = 0
pyautogui.DARWIN_CATCH_UP_TIME = 0

platform_name = "Linux"
BaseWrapper = Any


# ============================================================
# Screenshot (Linux: Xcursor + pyautogui)
# ============================================================
def _screenshot_linux(file_path: str):
    cursor_obj = Xcursor()
    imgarray = cursor_obj.getCursorImageArrayFast()
    cursor_img = Image.fromarray(imgarray)
    screenshot = pyautogui.screenshot()
    cursor_x, cursor_y = pyautogui.position()
    screenshot.paste(cursor_img, (cursor_x, cursor_y), cursor_img)
    screenshot.save(file_path)


@app.route('/screenshot', methods=['GET'])
def capture_screen_with_cursor():
    """Linux-specific screenshot endpoint. Defined here (not in common.py) to avoid
    a Python late-binding issue where the route would capture common._screenshot_linux
    (a stub raising NotImplementedError) instead of this real implementation."""
    file_path = os.path.join(os.path.dirname(__file__), "screenshots", "screenshot.png")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    _screenshot_linux(file_path)
    return send_file(file_path, mimetype='image/png')


# ============================================================
# Accessibility tree (Linux: pyatspi / AT-SPI)
# ============================================================
libreoffice_version_tuple: Optional[Tuple[int, ...]] = None


def _get_libreoffice_version() -> Tuple[int, ...]:
    result = subprocess.run("libreoffice --version", shell=True, text=True, stdout=subprocess.PIPE)
    version_str = result.stdout.split()[1]
    return tuple(map(int, version_str.split(".")))


def _create_atspi_node(node: Accessible, depth: int = 0, flag: Optional[str] = None) -> lxml.etree._Element:
    node_name = node.name
    attribute_dict: Dict[str, Any] = {"name": node_name}

    # States
    states: List[StateType] = node.getState().get_states()
    for st in states:
        state_name: str = StateType._enum_lookup[st]
        state_name = state_name.split("_", maxsplit=1)[1].lower()
        if len(state_name) == 0:
            continue
        attribute_dict["{{{:}}}{:}".format(_accessibility_ns_map_ubuntu["st"], state_name)] = "true"

    # Attributes
    attributes: Dict[str, str] = node.get_attributes()
    for attribute_name, attribute_value in attributes.items():
        if len(attribute_name) == 0:
            continue
        attribute_dict["{{{:}}}{:}".format(_accessibility_ns_map_ubuntu["attr"], attribute_name)] = attribute_value

    # Component
    if attribute_dict.get("{{{:}}}visible".format(_accessibility_ns_map_ubuntu["st"]), "false") == "true" \
            and attribute_dict.get("{{{:}}}showing".format(_accessibility_ns_map_ubuntu["st"]), "false") == "true":
        try:
            component: Component = node.queryComponent()
        except NotImplementedError:
            pass
        else:
            bbox: Sequence[int] = component.getExtents(pyatspi.XY_SCREEN)
            attribute_dict["{{{:}}}screencoord".format(_accessibility_ns_map_ubuntu["cp"])] = \
                str(tuple(bbox[0:2]))
            attribute_dict["{{{:}}}size".format(_accessibility_ns_map_ubuntu["cp"])] = str(tuple(bbox[2:]))

    # Text
    text = ""
    try:
        text_obj: ATText = node.queryText()
        text = text_obj.getText(0, text_obj.characterCount)
        text = text.replace("\ufffc", "").replace("\ufffd", "")
    except NotImplementedError:
        pass

    # Image, Selection, Value, Action
    try:
        node.queryImage()
        attribute_dict["image"] = "true"
    except NotImplementedError:
        pass

    try:
        node.querySelection()
        attribute_dict["selection"] = "true"
    except NotImplementedError:
        pass

    try:
        value: ATValue = node.queryValue()
        value_key = f"{{{_accessibility_ns_map_ubuntu['val']}}}"
        for attr_name, attr_func in [
            ("value", lambda: value.currentValue),
            ("min", lambda: value.minimumValue),
            ("max", lambda: value.maximumValue),
            ("step", lambda: value.minimumIncrement)
        ]:
            try:
                attribute_dict[f"{value_key}{attr_name}"] = str(attr_func())
            except:
                pass
    except NotImplementedError:
        pass

    try:
        action: ATAction = node.queryAction()
        for i in range(action.nActions):
            action_name = action.getName(i).replace(" ", "-")
            attribute_dict["{{{:}}}{:}_desc".format(_accessibility_ns_map_ubuntu["act"], action_name)] = action.getDescription(i)
            attribute_dict["{{{:}}}{:}_kb".format(_accessibility_ns_map_ubuntu["act"], action_name)] = action.getKeyBinding(i)
    except NotImplementedError:
        pass

    raw_role_name = node.getRoleName().strip()
    node_role_name = (raw_role_name or "unknown").replace(" ", "-")

    if not flag:
        if raw_role_name == "document spreadsheet":
            flag = "calc"
        if raw_role_name == "application" and node.name == "Thunderbird":
            flag = "thunderbird"

    xml_node = lxml.etree.Element(
        node_role_name,
        attrib=attribute_dict,
        nsmap=_accessibility_ns_map_ubuntu
    )

    if len(text) > 0:
        xml_node.text = text

    if depth == MAX_DEPTH:
        logger.warning("Max depth reached")
        return xml_node

    if flag == "calc" and node_role_name == "table":
        global libreoffice_version_tuple
        MAXIMUN_COLUMN = 1024 if libreoffice_version_tuple < (7, 4) else 16384
        MAX_ROW = 104_8576

        index_base = 0
        first_showing = False
        column_base = None
        for r in range(MAX_ROW):
            for clm in range(column_base or 0, MAXIMUN_COLUMN):
                child_node: Accessible = node[index_base + clm]
                showing: bool = child_node.getState().contains(STATE_SHOWING)
                if showing:
                    child_node: lxml.etree._Element = _create_atspi_node(child_node, depth + 1, flag)
                    if not first_showing:
                        column_base = clm
                        first_showing = True
                    xml_node.append(child_node)
                elif first_showing and column_base is not None or clm >= 500:
                    break
            if first_showing and clm == column_base or not first_showing and r >= 500:
                break
            index_base += MAXIMUN_COLUMN
        return xml_node
    else:
        try:
            for i, ch in enumerate(node):
                if i == MAX_WIDTH:
                    logger.warning("Max width reached")
                    break
                xml_node.append(_create_atspi_node(ch, depth + 1, flag))
        except:
            logger.warning("Error occurred during children traversing. Has Ignored. Node: %s",
                           lxml.etree.tostring(xml_node, encoding="unicode"))
        return xml_node


def _has_active_terminal(desktop: Accessible) -> bool:
    for app in desktop:
        if app.getRoleName() == "application" and app.name == "gnome-terminal-server":
            for frame in app:
                if frame.getRoleName() == "frame" and frame.getState().contains(pyatspi.STATE_ACTIVE):
                    return True
    return False


@app.route('/terminal', methods=['GET'])
def get_terminal_output():
    try:
        desktop: Accessible = pyatspi.Registry.getDesktop(0)
        if _has_active_terminal(desktop):
            desktop_xml: lxml.etree._Element = _create_atspi_node(desktop)
            xpath = '//application[@name="gnome-terminal-server"]/frame[@st:active="true"]//terminal[@st:focused="true"]'
            terminals: List[lxml.etree._Element] = desktop_xml.xpath(xpath, namespaces=_accessibility_ns_map_ubuntu)
            output = terminals[0].text.rstrip() if len(terminals) == 1 else None
        else:
            output = None
        return jsonify({"output": output, "status": "success"})
    except Exception as e:
        logger.error("Failed to get terminal output. Error: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/accessibility", methods=["GET"])
def get_accessibility_tree():
    try:
        global libreoffice_version_tuple
        libreoffice_version_tuple = _get_libreoffice_version()

        desktop: Accessible = pyatspi.Registry.getDesktop(0)
        xml_node = lxml.etree.Element("desktop-frame", nsmap=_accessibility_ns_map_ubuntu)

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(_create_atspi_node, app_node, 1) for app_node in desktop]
            for future in concurrent.futures.as_completed(futures):
                xml_tree = future.result()
                xml_node.append(xml_tree)

        return jsonify({"AT": lxml.etree.tostring(xml_node, encoding="unicode")})
    except Exception as e:
        logger.error("Accessibility tree generation failed: %s", e)
        return jsonify({"AT": "", "error": str(e)}), 500


# ============================================================
# Screen size (Linux: Xlib)
# ============================================================
@app.route('/screen_size', methods=['POST'])
def get_screen_size():
    d = display.Display()
    screen_width = d.screen().width_in_pixels
    screen_height = d.screen().height_in_pixels
    return jsonify({"width": screen_width, "height": screen_height})


@app.route('/window_size', methods=['POST'])
def get_window_size():
    if 'app_class_name' in request.form:
        app_class_name = request.form['app_class_name']
    else:
        return jsonify({"error": "app_class_name is required"}), 400

    d = display.Display()
    root = d.screen().root
    window_ids = root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType).value

    for window_id in window_ids:
        try:
            window = d.create_resource_object('window', window_id)
            wm_class = window.get_wm_class()
            if wm_class is None:
                continue
            if app_class_name.lower() in [name.lower() for name in wm_class]:
                geom = window.get_geometry()
                return jsonify({"width": geom.width, "height": geom.height})
        except Exception:
            continue
    return None


# ============================================================
# Recording (Linux: ffmpeg x11grab)
# ============================================================
@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_process
    if recording_process:
        return jsonify({'status': 'error', 'message': 'Recording is already in progress.'}), 400

    d = display.Display()
    screen_width = d.screen().width_in_pixels
    screen_height = d.screen().height_in_pixels

    start_command = f"ffmpeg -y -f x11grab -draw_mouse 1 -s {screen_width}x{screen_height} -i :0.0 -c:v libx264 -r 30 {recording_path}"
    recording_process = subprocess.Popen(
        shlex.split(start_command),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return jsonify({'status': 'success', 'message': 'Started recording.'})


@app.route('/end_recording', methods=['POST'])
def end_recording():
    global recording_process
    if not recording_process:
        return jsonify({'status': 'error', 'message': 'No recording in progress to stop.'}), 400

    recording_process.send_signal(signal.SIGINT)
    recording_process.wait()
    recording_process = None

    if os.path.exists(recording_path):
        return send_file(recording_path, as_attachment=True)
    else:
        return send_file("Recording failed"), 404


# ============================================================
# Wallpaper (Linux: gsettings)
# ============================================================
def _change_wallpaper_linux(path: Path):
    subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", f"file://{path}"])


# ============================================================
# Window management (Linux: wmctrl)
# ============================================================
def _activate_window_linux(window_name: str, strict: bool, by_class_name: bool):
    subprocess.run([
        "wmctrl",
        "-{:}{:}a".format(
            "x" if by_class_name else "",
            "F" if strict else ""
        ),
        window_name
    ])
    return "Window activated successfully", 200


def _close_window_linux(window_name: str, strict: bool, by_class_name: bool):
    subprocess.run([
        "wmctrl",
        "-{:}{:}c".format(
            "x" if by_class_name else "",
            "F" if strict else ""
        ),
        window_name
    ])
    return "Window closed successfully.", 200


# ============================================================
# Chrome Playwright Page DOM Endpoint
# Connects to Chrome via CDP (remote debugging port) and returns
# the DOM structure + accessibility info for the active page.
# This allows the agent to interact with web pages in Chrome,
# which AT-SPI cannot capture natively.
# ============================================================
@app.route('/playwright_page', methods=['GET'])
def get_playwright_page():
    import json as _json

    # Try to connect to Chrome via CDP WebSocket
    # The Chrome remote debugging HTTP endpoint lists all pages/tabs
    chrome_debug_urls = [
        "http://127.0.0.1:9222/json",
        "http://127.0.0.1:1337/json",
    ]

    ws_url = None
    page_info = None

    for debug_url in chrome_debug_urls:
        try:
            resp = requests.get(debug_url, timeout=5)
            if resp.status_code == 200:
                pages = resp.json()
                # Find the first non-empty, non-chrome:// page
                for page in pages:
                    if page.get("type") == "page" and page.get("url") and \
                       not page["url"].startswith("chrome://") and \
                       not page["url"].startswith("about:"):
                        ws_url = page.get("webSocketDebuggerUrl")
                        page_info = {
                            "url": page.get("url"),
                            "title": page.get("title", ""),
                            "id": page.get("id", ""),
                        }
                        break
                if ws_url:
                    break
        except Exception:
            continue

    if not ws_url:
        return jsonify({
            "status": "no_chrome",
            "message": "Chrome is not running with remote debugging enabled. "
                       "Start Chrome with: google-chrome --remote-debugging-port=9222"
        }), 200

    # Use Python's built-in http.client + hashlib for WebSocket handshake
    try:
        import http.client
        import hashlib
        import base64
        import struct
        import threading
        import time as _time
    except ImportError:
        return jsonify({
            "status": "missing_dep",
            "message": "Internal Python modules not available (should never happen)"
        }), 200

    # Parse WebSocket URL
    import re as _re
    ws_match = _re.match(r"ws://([^:]+):(\d+)(.+)", ws_url)
    if not ws_match:
        return jsonify({
            "status": "ws_error",
            "message": f"Invalid WebSocket URL format: {ws_url}"
        }), 200
    ws_host, ws_port_str, ws_path = ws_match.groups()
    ws_port = int(ws_port_str)

    class _SimpleWS:
        """Minimal WebSocket client using only stdlib (no third-party deps)."""
        def __init__(self):
            self.sock = None
            self.connected = False
            self._recv_buf = b""

        def connect(self, host, port, path):
            import socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((host, port))

            # WebSocket handshake
            key = base64.b64encode(os.urandom(16)).decode('utf-8')
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"\r\n"
            )
            self.sock.sendall(handshake.encode('utf-8'))
            resp = b""
            while b"\r\n\r\n" not in resp:
                resp += self.sock.recv(4096)
            if b"HTTP/1.1 101" not in resp and b"HTTP/1.0 101" not in resp:
                raise Exception(f"WebSocket handshake failed: {resp[:200]}")
            self.connected = True

        def _pack_frame(self, data: bytes, opcode: int) -> bytes:
            length = len(data)
            payload = bytearray()
            payload.append(0x80 | opcode)  # FIN + opcode
            if length < 126:
                payload.append(0x80 | length)  # MASK + length
            elif length < 65536:
                payload.append(0x80 | 126)
                payload.extend(struct.pack(">H", length))
            else:
                payload.append(0x80 | 127)
                payload.extend(struct.pack(">Q", length))
            # Mask with random 4 bytes
            mask = os.urandom(4)
            masked = bytes(a ^ b for a, b in zip(data, (mask * (len(data) // 4 + 1))[:len(data)]))
            payload.extend(mask)
            payload.extend(masked)
            return bytes(payload)

        def _unpack_frame(self) -> bytes:
            if len(self._recv_buf) < 2:
                self._recv_buf += self.sock.recv(4096)
            payload = self._recv_buf[:2]
            if len(payload) < 2:
                return b""
            opcode = payload[0] & 0x0F
            length = payload[1] & 0x7F
            idx = 2
            if length == 126:
                self._recv_buf += self.sock.recv(4096)
                length = struct.unpack(">H", self._recv_buf[idx:idx+2])[0]
                idx += 2
            elif length == 127:
                self._recv_buf += self.sock.recv(4096)
                length = struct.unpack(">Q", self._recv_buf[idx:idx+8])[0]
                idx += 8
            while len(self._recv_buf) < idx + length:
                self._recv_buf += self.sock.recv(4096)
            data = self._recv_buf[idx:idx+length]
            self._recv_buf = self._recv_buf[idx+length:]
            if opcode == 1:  # text
                return data.decode('utf-8', errors='replace')
            elif opcode == 0x8:  # close
                self.connected = False
                return ""
            return b""

        def send(self, msg: str):
            frame = self._pack_frame(msg.encode('utf-8'), opcode=1)
            self.sock.sendall(frame)

        def recv(self) -> str:
            while self.connected:
                data = self._unpack_frame()
                if data:
                    return data
            return ""

        def close(self):
            try:
                self.sock.close()
            except Exception:
                pass
            self.connected = False

    try:
        ws = _SimpleWS()
        ws.connect(ws_host, ws_port, ws_path)
    except Exception as e:
        return jsonify({
            "status": "ws_error",
            "message": f"Failed to connect to Chrome WebSocket: {e}"
        }), 200

    def send_cdp(command: dict) -> dict:
        import threading
        import time as _time
        result = {}
        result_ready = threading.Event()
        result_lock = threading.Lock()
        msg_id = command.get("id", 1)

        def on_message(ws_msg):
            nonlocal result
            try:
                data = _json.loads(ws_msg)
                if isinstance(data, dict) and data.get("id") == msg_id:
                    with result_lock:
                        result = data.get("result", {})
                    result_ready.set()
            except Exception:
                pass

        def reader():
            while not result_ready.is_set() and ws.connected:
                try:
                    msg = ws.recv()
                    if msg:
                        on_message(msg)
                except Exception:
                    break
                _time.sleep(0.05)

        reader_thread = threading.Thread(target=reader, daemon=True)
        reader_thread.start()

        ws.send(_json.dumps(command))
        result_ready.wait(timeout=10)
        reader_thread.join(timeout=1)

        return result

    # 1. Get DOM snapshot via Runtime.evaluate
    dom_result = send_cdp({
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {
            "expression": """
                (() => {
                    const snap = {};
                    function walk(node, path) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const tag = node.tagName.toLowerCase();
                            const id = node.id ? '#' + node.id : '';
                            const cls = node.className && typeof node.className === 'string'
                                ? '.' + node.className.trim().split(/\\s+/).join('.') : '';
                            const name = tag + id + cls;
                            const rect = node.getBoundingClientRect();
                            const visible = rect.width > 0 && rect.height > 0;
                            const text = node.innerText ? node.innerText.trim().slice(0, 200) : '';

                            // Collect data-* attributes as "data" object
                            const dataAttrs = {};
                            for (const attr of node.attributes) {
                                if (attr.name.startsWith('data-')) {
                                    dataAttrs[attr.name.slice(5)] = attr.value.slice(0, 500);
                                }
                            }

                            const children = [];
                            for (const child of node.children) {
                                const childResult = walk(child, path + ' > ' + tag);
                                if (childResult) children.push(childResult);
                            }
                            return {
                                name,
                                tag,
                                id: node.id || null,
                                cls: node.className && typeof node.className === 'string'
                                    ? node.className.trim().split(/\\s+/) : [],
                                text,
                                visible,
                                rect: visible ? {x: rect.x, y: rect.y, w: rect.width, h: rect.height} : null,
                                data: Object.keys(dataAttrs).length ? dataAttrs : null,
                                children: children.length ? children : null,
                                // role via ARIA
                                role: node.getAttribute('role') || null,
                                // aria-label
                                ariaLabel: node.getAttribute('aria-label') || null,
                                // placeholder
                                placeholder: node.getAttribute('placeholder') || null,
                                // href for links
                                href: node.tagName.toLowerCase() === 'a' ? node.href : null,
                                // type for inputs
                                inputType: node.tagName.toLowerCase() === 'input' ? node.type : null,
                                // live form state
                                value: (node.tagName.toLowerCase() === 'input' ||
                                        node.tagName.toLowerCase() === 'textarea' ||
                                        node.tagName.toLowerCase() === 'select') ? node.value : null,
                                checked: node.tagName.toLowerCase() === 'input' ? !!node.checked : null,
                            };
                        }
                        return null;
                    }
                    const root = document.getElementById('app') || document.body;
                    return JSON.stringify(walk(root));
                })()
            """,
            "returnByValue": True,
            "timeout": 10000,
        }
    })

    # 2. Get accessibility snapshot for the page via Accessibility.getFullAXTree
    a11y_result = send_cdp({
        "id": 2,
        "method": "Accessibility.getFullAXTree",
        "params": {}
    })

    # 3. Get localStorage and visible controls for cross-platform state metrics.
    storage_result = send_cdp({
        "id": 3,
        "method": "Runtime.evaluate",
        "params": {
            "expression": """
                JSON.stringify({
                    localStorage: Object.fromEntries(
                        Array.from({length: localStorage.length}, (_, i) => {
                            const key = localStorage.key(i);
                            return [key, localStorage.getItem(key)];
                        })
                    ),
                    controls: Array.from(document.querySelectorAll('input, textarea, select, button, a')).map((el) => {
                        const rect = el.getBoundingClientRect();
                        return {
                            tag: el.tagName.toLowerCase(),
                            id: el.id || null,
                            name: el.name || null,
                            type: el.type || null,
                            text: (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().slice(0, 500),
                            value: (el.tagName.toLowerCase() === 'input' || el.tagName.toLowerCase() === 'textarea' || el.tagName.toLowerCase() === 'select') ? el.value : null,
                            checked: el.tagName.toLowerCase() === 'input' ? !!el.checked : null,
                            visible: rect.width > 0 && rect.height > 0,
                            disabled: !!el.disabled,
                            rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height},
                        };
                    }),
                    bodyText: (document.body && document.body.innerText || '').slice(0, 5000),
                })
            """,
            "returnByValue": True,
        }
    })

    # 4. Get viewport/screenshot area
    viewport_result = send_cdp({
        "id": 4,
        "method": "Runtime.evaluate",
        "params": {
            "expression": """
                JSON.stringify({
                    width: window.innerWidth,
                    height: window.innerHeight,
                    scrollX: window.scrollX,
                    scrollY: window.scrollY,
                })
            """,
            "returnByValue": True,
        }
    })

    # Clean up: close the WebSocket connection
    try:
        ws.close()
    except Exception:
        pass

    return jsonify({
        "status": "ok",
        "page": page_info,
        "dom": json.loads(dom_result.get("result", {}).get("result", {}).get("value", "{}"))
                if dom_result.get("result", {}).get("result", {}).get("value") else {},
        "a11y": a11y_result.get("nodes", []),
        "state": json.loads(storage_result.get("result", {}).get("result", {}).get("value", "{}"))
                 if storage_result.get("result", {}).get("result", {}).get("value") else {},
        "viewport": json.loads(viewport_result.get("result", {}).get("result", {}).get("value", "{}"))
                   if viewport_result.get("result", {}).get("result", {}).get("value") else {},
    })


# ============================================================
# Chrome CDP Navigation Endpoint
# Opens a URL in the Chrome browser via CDP (remote debugging).
# Usage: POST /chrome_navigate  {"url": "http://..."}
# ============================================================
@app.route('/chrome_navigate', methods=['POST'])
def chrome_navigate():
    import json as _json
    target_url = None
    try:
        body = request.get_json(silent=True) or {}
        target_url = body.get("url", "")
        if not target_url:
            return jsonify({"status": "error", "message": "url parameter required"}), 400
    except Exception:
        return jsonify({"status": "error", "message": "invalid JSON body"}), 400

    chrome_debug_urls = [
        "http://127.0.0.1:9222/json",
        "http://127.0.0.1:1337/json",
    ]

    ws_url = None
    page_id = None
    for debug_url in chrome_debug_urls:
        try:
            resp = requests.get(debug_url, timeout=5)
            if resp.status_code == 200:
                pages = resp.json()
                for page in pages:
                    if page.get("type") == "page":
                        ws_url = page.get("webSocketDebuggerUrl")
                        page_id = page.get("id")
                        break
                if ws_url:
                    break
        except Exception:
            continue

    if not ws_url:
        return jsonify({
            "status": "no_chrome",
            "message": "Chrome is not running with remote debugging enabled. "
                       "Start Chrome with: google-chrome --remote-debugging-port=9222"
        }), 200

    import http.client, re as _re, base64, struct, socket, threading

    ws_match = _re.match(r"ws://([^:]+):(\d+)(.+)", ws_url)
    if not ws_match:
        return jsonify({"status": "ws_error", "message": f"Invalid WebSocket URL: {ws_url}"}), 200

    ws_host, ws_port_str, ws_path = ws_match.groups()
    ws_port = int(ws_port_str)

    class _WS:
        def __init__(self):
            self.sock = None
            self.connected = False
            self._buf = b""
        def connect(self, host, port, path):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(15)
            self.sock.connect((host, port))
            key = base64.b64encode(os.urandom(16)).decode('utf-8')
            hs = (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n"
                  f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
                  f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
            self.sock.sendall(hs.encode())
            resp = b""
            while b"\r\n\r\n" not in resp:
                resp += self.sock.recv(4096)
            if b"101" not in resp:
                raise Exception(f"WS handshake failed: {resp[:200]}")
            self.connected = True
        def _pf(self, d, o):
            n = len(d); p = bytearray(); p.append(0x80|o)
            if n < 126: p.append(0x80|n)
            elif n < 65536: p.append(0x80|126); p.extend(struct.pack(">H", n))
            else: p.append(0x80|127); p.extend(struct.pack(">Q", n))
            m = os.urandom(4)
            masked = bytes(a^b for a,b in zip(d, (m*(n//4+1))[:n]))
            return bytes(p+m+masked)
        def send(self, m): self.sock.sendall(self._pf(m.encode('utf-8'), 1))
        def _unpack(self):
            while len(self._buf) < 2: self._buf += self.sock.recv(4096)
            op = self._buf[0]&0x0F; l = self._buf[1]&0x7F; i = 2
            if l == 126: self._buf += self.sock.recv(4096); l = struct.unpack(">H", self._buf[i:i+2])[0]; i += 2
            elif l == 127: self._buf += self.sock.recv(4096); l = struct.unpack(">Q", self._buf[i:i+8])[0]; i += 8
            while len(self._buf) < i+l: self._buf += self.sock.recv(4096)
            d = self._buf[i:i+l]; self._buf = self._buf[i+l:]
            return d.decode('utf-8','replace') if op == 1 else b""
        def recv(self):
            while self.connected:
                d = self._unpack()
                if d: return d
            return ""
        def close(self):
            try: self.sock.close()
            except: pass
            self.connected = False

    try:
        ws = _WS()
        ws.connect(ws_host, ws_port, ws_path)
    except Exception as e:
        return jsonify({"status": "ws_error", "message": f"WS connect failed: {e}"}), 200

    result = {}
    ready = threading.Event()

    def reader():
        while not ready.is_set() and ws.connected:
            try:
                msg = ws.recv()
                if msg:
                    try:
                        d = _json.loads(msg)
                        if d.get("id") == 99:
                            with threading.Lock():
                                result["navigate"] = d.get("result", {})
                            ready.set()
                    except: pass
            except: pass

    t = threading.Thread(target=reader, daemon=True)
    t.start()

    ws.send(_json.dumps({"id": 99, "method": "Page.navigate", "params": {"url": target_url}}))

    # Wait up to 20s for navigation result
    ready.wait(timeout=20)
    ws.close()

    if result:
        frame_id = result.get("navigate", {}).get("frameId", "")
        return jsonify({
            "status": "ok",
            "url": target_url,
            "frameId": frame_id,
        })
    else:
        # Navigation was sent; Chrome may still be loading
        return jsonify({
            "status": "navigating",
            "url": target_url,
            "message": "Navigation command sent",
        })


# ============================================================
# Entry point
# ============================================================
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
