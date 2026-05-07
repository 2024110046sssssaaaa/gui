"""
main_windows.py - OSWorld server for Windows VMs.

Run inside the Windows VM to provide screenshot, accessibility tree,
and desktop automation capabilities via HTTP endpoints.

Usage:
    python main_windows.py

Requires (pre-installed in the VM):
    pip install flask pyautogui lxml pillow requests pywinauto pywin32 pygetwindow

The server listens on 0.0.0.0:5000 inside the VM. The host machine
communicates with it via PythonController (HTTP client).
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyautogui
import requests
import lxml.etree
from flask import Flask, jsonify, request, send_file

# Windows-specific imports
from pywinauto import Desktop
from pywinauto.base_wrapper import BaseWrapper
import pywinauto.application
import win32ui, win32gui

# Import ALL shared routes from common.py
from common import (
    app,
    MAX_DEPTH,
    MAX_WIDTH,
    _accessibility_ns_map_windows,
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

platform_name = "Windows"
Accessible = Any
BaseWrapper_Win = BaseWrapper


# ============================================================
# Screenshot (Windows: win32gui cursor overlay + PIL ImageGrab)
# ============================================================
def _screenshot_windows(file_path: str):
    def get_cursor():
        hcursor = win32gui.GetCursorInfo()[1]
        hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, 36, 36)
        hdc = hdc.CreateCompatibleDC()
        hdc.SelectObject(hbmp)
        hdc.DrawIcon((0, 0), hcursor)

        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)
        cursor = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1).convert("RGBA")

        win32gui.DestroyIcon(hcursor)
        win32gui.DeleteObject(hbmp.GetHandle())
        hdc.DeleteDC()

        pixdata = cursor.load()
        width, height = cursor.size
        for y in range(height):
            for x in range(width):
                if pixdata[x, y] == (0, 0, 0, 255):
                    pixdata[x, y] = (0, 0, 0, 0)

        hotspot = win32gui.GetIconInfo(hcursor)[1:3]
        return (cursor, hotspot)

    from PIL import Image, ImageGrab

    ratio = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
    img = ImageGrab.grab(bbox=None, include_layered_windows=True)

    try:
        cursor, (hotspotx, hotspoty) = get_cursor()
        pos_win = win32gui.GetCursorPos()
        pos = (round(pos_win[0] * ratio - hotspotx), round(pos_win[1] * ratio - hotspoty))
        img.paste(cursor, pos, cursor)
    except:
        pass

    img.save(file_path)


@app.route('/screenshot', methods=['GET'])
def capture_screen_with_cursor():
    """Windows-specific screenshot endpoint. Defined here (not in common.py) to avoid
    a Python late-binding issue where the route would capture common._screenshot_windows
    (a stub raising NotImplementedError) instead of this real implementation."""
    import os as _os
    file_path = _os.path.join(_os.path.dirname(__file__), "screenshots", "screenshot.png")
    _os.makedirs(_os.path.dirname(file_path), exist_ok=True)
    _screenshot_windows(file_path)
    return send_file(file_path, mimetype='image/png')


# ============================================================
# Accessibility tree (Windows: pywinauto / UIA backend)
# ============================================================
def _create_pywinauto_node(node, nodes, depth: int = 0, flag: Optional[str] = None) -> lxml.etree._Element:
    nodes = nodes or set()
    if node in nodes:
        return
    nodes.add(node)

    attribute_dict: Dict[str, Any] = {"name": node.element_info.name}

    base_properties = {}
    try:
        base_properties.update(node.get_properties())
    except:
        try:
            _element_class = node.__class__
            class TempElement(node.__class__):
                writable_props = pywinauto.base_wrapper.BaseWrapper.writable_props
            node.__class__ = TempElement
            properties = node.get_properties()
            node.__class__ = _element_class
            base_properties.update(properties)
        except Exception as e:
            logger.error(e)
            pass

    # Count-cnt
    for attr_name in ["control_count", "button_count", "item_count", "column_count"]:
        try:
            attribute_dict[f"{{{_accessibility_ns_map_windows['st']}}}{attr_name}"] = base_properties[attr_name].lower()
        except:
            pass

    # Columns-cols
    try:
        attribute_dict[f"{{{_accessibility_ns_map_windows['st']}}}columns"] = base_properties["columns"].lower()
    except:
        pass

    # Id-id
    for attr_name in ["control_id", "automation_id", "window_id"]:
        try:
            attribute_dict[f"{{{_accessibility_ns_map_windows['st']}}}{attr_name}"] = base_properties[attr_name].lower()
        except:
            pass

    # States
    for attr_name, attr_func in [
        ("enabled", lambda: node.is_enabled()),
        ("visible", lambda: node.is_visible()),
        ("minimized", lambda: node.is_minimized()),
        ("maximized", lambda: node.is_maximized()),
        ("normal", lambda: node.is_normal()),
        ("unicode", lambda: node.is_unicode()),
        ("collapsed", lambda: node.is_collapsed()),
        ("checkable", lambda: node.is_checkable()),
        ("checked", lambda: node.is_checked()),
        ("focused", lambda: node.is_focused()),
        ("keyboard_focused", lambda: node.is_keyboard_focused()),
        ("selected", lambda: node.is_selected()),
        ("selection_required", lambda: node.is_selection_required()),
        ("pressable", lambda: node.is_pressable()),
        ("pressed", lambda: node.is_pressed()),
        ("expanded", lambda: node.is_expanded()),
        ("editable", lambda: node.is_editable()),
        ("has_keyboard_focus", lambda: node.has_keyboard_focus()),
        ("is_keyboard_focusable", lambda: node.is_keyboard_focusable()),
    ]:
        try:
            attribute_dict[f"{{{_accessibility_ns_map_windows['st']}}}{attr_name}"] = str(attr_func()).lower()
        except:
            pass

    # Component
    try:
        rectangle = node.rectangle()
        attribute_dict["{{{:}}}screencoord".format(_accessibility_ns_map_windows["cp"])] = \
            "({:d}, {:d})".format(rectangle.left, rectangle.top)
        attribute_dict["{{{:}}}size".format(_accessibility_ns_map_windows["cp"])] = \
            "({:d}, {:d})".format(rectangle.width(), rectangle.height())
    except Exception as e:
        logger.error("Error accessing rectangle: ", e)

    # Text
    text: str = node.window_text()
    if text == attribute_dict["name"]:
        text = ""

    # Selection
    if hasattr(node, "select"):
        attribute_dict["selection"] = "true"

    # Value
    for attr_name, attr_funcs in [
        ("step", [lambda: node.get_step()]),
        ("value", [lambda: node.value(), lambda: node.get_value(), lambda: node.get_position()]),
        ("min", [lambda: node.min_value(), lambda: node.get_range_min()]),
        ("max", [lambda: node.max_value(), lambda: node.get_range_max()])
    ]:
        for attr_func in attr_funcs:
            if hasattr(node, attr_func.__name__):
                try:
                    attribute_dict[f"{{{_accessibility_ns_map_windows['val']}}}{attr_name}"] = str(attr_func())
                    break
                except:
                    pass

    attribute_dict["{{{:}}}class".format(_accessibility_ns_map_windows["class"])] = str(type(node))

    # class_name
    for attr_name in ["class_name", "friendly_class_name"]:
        try:
            attribute_dict[f"{{{_accessibility_ns_map_windows['class']}}}{attr_name}"] = base_properties[attr_name].lower()
        except:
            pass

    node_role_name: str = node.class_name().lower().replace(" ", "-")
    node_role_name = "".join(
        map(lambda _ch: _ch if _ch.isidentifier() or _ch in {"-"} or _ch.isalnum() else "-", node_role_name))

    if node_role_name.strip() == "":
        node_role_name = "unknown"
    if not node_role_name[0].isalpha():
        node_role_name = "tag" + node_role_name

    xml_node = lxml.etree.Element(
        node_role_name,
        attrib=attribute_dict,
        nsmap=_accessibility_ns_map_windows
    )

    if text is not None and len(text) > 0 and text != attribute_dict["name"]:
        xml_node.text = text

    if depth == MAX_DEPTH:
        logger.warning("Max depth reached")
        return xml_node

    # use multi thread to accelerate children fetching
    children = node.children()
    if children:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_child = [executor.submit(_create_pywinauto_node, ch, nodes, depth + 1, flag) for ch in children[:MAX_WIDTH]]
        try:
            xml_node.extend([future.result() for future in concurrent.futures.as_completed(future_to_child)])
        except Exception as e:
            logger.error(f"Exception occurred: {e}")

    return xml_node


@app.route("/accessibility", methods=["GET"])
def get_accessibility_tree():
    desktop: Desktop = Desktop(backend="uia")
    xml_node = lxml.etree.Element("desktop", nsmap=_accessibility_ns_map_windows)

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(_create_pywinauto_node, wnd, {}, 1) for wnd in desktop.windows()]
        for future in concurrent.futures.as_completed(futures):
            xml_tree = future.result()
            xml_node.append(xml_tree)

    return jsonify({"AT": lxml.etree.tostring(xml_node, encoding="unicode")})


# ============================================================
# Screen size (Windows: GetSystemMetrics)
# ============================================================
@app.route('/screen_size', methods=['POST'])
def get_screen_size():
    user32 = ctypes.windll.user32
    screen_width: int = user32.GetSystemMetrics(0)
    screen_height: int = user32.GetSystemMetrics(1)
    return jsonify({"width": screen_width, "height": screen_height})


@app.route('/window_size', methods=['POST'])
def get_window_size():
    import pygetwindow as gw
    if 'app_class_name' in request.form:
        app_class_name = request.form['app_class_name']
    else:
        return jsonify({"error": "app_class_name is required"}), 400

    windows = gw.getWindowsWithTitle(app_class_name)
    if windows:
        w = windows[0]
        return jsonify({"width": w.width, "height": w.height})
    return None


# ============================================================
# Terminal output (Windows - not implemented)
# ============================================================
@app.route('/terminal', methods=['GET'])
def get_terminal_output():
    return "Currently not implemented for Windows.", 500


# ============================================================
# Recording (Windows - not implemented; use ffmpeg with gdigrab)
# ============================================================
@app.route('/start_recording', methods=['POST'])
def start_recording():
    return "Recording not yet implemented for Windows.", 501


@app.route('/end_recording', methods=['POST'])
def end_recording():
    return "Recording not yet implemented for Windows.", 501


# ============================================================
# Wallpaper (Windows: SystemParametersInfoW)
# ============================================================
def _change_wallpaper_windows(path: Path):
    ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path), 3)


# ============================================================
# Window management (Windows: pygetwindow)
# ============================================================
def _activate_window_windows(window_name: str, strict: bool):
    import pygetwindow as gw

    windows: List[gw.Window] = gw.getWindowsWithTitle(window_name)
    window: Optional[gw.Window] = None

    if len(windows) == 0:
        return "Window {:} not found (empty results)".format(window_name), 404
    elif strict:
        for wnd in windows:
            if wnd.title == wnd:
                window = wnd
        if window is None:
            return "Window {:} not found (strict mode).".format(window_name), 404
    else:
        window = windows[0]

    window.activate()
    return "Window activated successfully", 200


def _close_window_windows(window_name: str, strict: bool):
    import pygetwindow as gw

    windows: List[gw.Window] = gw.getWindowsWithTitle(window_name)
    window: Optional[gw.Window] = None

    if len(windows) == 0:
        return "Window {:} not found (empty results)".format(window_name), 404
    elif strict:
        for wnd in windows:
            if wnd.title == wnd:
                window = wnd
        if window is None:
            return "Window {:} not found (strict mode).".format(window_name), 404
    else:
        window = windows[0]

    window.close()
    return "Window closed successfully.", 200


# ============================================================
# Entry point
# ============================================================
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
