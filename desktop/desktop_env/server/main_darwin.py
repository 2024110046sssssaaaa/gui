"""
main_darwin.py - OSWorld server for macOS VMs.

Run inside the macOS VM to provide screenshot, accessibility tree,
and desktop automation capabilities via HTTP endpoints.

Usage:
    python main_darwin.py

Requires (pre-installed in the VM):
    pip install flask pyautogui lxml pillow requests oa_atomacos

The server listens on 0.0.0.0:5000 inside the VM. The host machine
communicates with it via PythonController (HTTP client).
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pyautogui
import requests
import lxml.etree
from flask import Flask, jsonify, request, send_file

# macOS-specific imports
import plistlib
import AppKit
import ApplicationServices
import Foundation
import Quartz
import oa_atomacos

# Import ALL shared routes from common.py
from common import (
    app,
    MAX_DEPTH,
    MAX_WIDTH,
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

platform_name = "Darwin"
Accessible = Any
BaseWrapper = Any


# ============================================================
# Screenshot (macOS: screencapture -C includes cursor)
# ============================================================
def _screenshot_darwin(file_path: str):
    subprocess.run(["screencapture", "-C", file_path])


@app.route('/screenshot', methods=['GET'])
def capture_screen_with_cursor():
    """macOS-specific screenshot endpoint. Defined here (not in common.py) to avoid
    a Python late-binding issue where the route would capture common._screenshot_darwin
    (a stub raising NotImplementedError) instead of this real implementation."""
    file_path = os.path.join(os.path.dirname(__file__), "screenshots", "screenshot.png")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    _screenshot_darwin(file_path)
    return send_file(file_path, mimetype='image/png')


# ============================================================
# Accessibility tree (macOS: AXUI / AppKit)
# ============================================================
def _create_axui_node(node, nodes: Set = None, depth: int = 0, bbox: tuple = None):
    nodes = nodes or set()
    if node in nodes:
        return
    nodes.add(node)

    reserved_keys = {
        "AXEnabled": "st",
        "AXFocused": "st",
        "AXFullScreen": "st",
        "AXTitle": "attr",
        "AXChildrenInNavigationOrder": "attr",
        "AXChildren": "attr",
        "AXFrame": "attr",
        "AXRole": "role",
        "AXHelp": "attr",
        "AXRoleDescription": "role",
        "AXSubrole": "role",
        "AXURL": "attr",
        "AXValue": "val",
        "AXDescription": "attr",
        "AXDOMIdentifier": "attr",
        "AXSelected": "st",
        "AXInvalid": "st",
        "AXRows": "attr",
        "AXColumns": "attr",
    }
    attribute_dict = {}

    if depth == 0:
        bbox = (
            node["kCGWindowBounds"]["X"],
            node["kCGWindowBounds"]["Y"],
            node["kCGWindowBounds"]["X"] + node["kCGWindowBounds"]["Width"],
            node["kCGWindowBounds"]["Y"] + node["kCGWindowBounds"]["Height"]
        )
        app_ref = ApplicationServices.AXUIElementCreateApplication(node["kCGWindowOwnerPID"])

        attribute_dict["name"] = node["kCGWindowOwnerName"]
        if attribute_dict["name"] != "Dock":
            error_code, app_wins_ref = ApplicationServices.AXUIElementCopyAttributeValue(
                app_ref, "AXWindows", None)
            if error_code:
                logger.error("MacOS parsing %s encountered Error code: %d", app_ref, error_code)
        else:
            app_wins_ref = [app_ref]
        node = app_wins_ref[0]

    error_code, attr_names = ApplicationServices.AXUIElementCopyAttributeNames(node, None)

    if error_code:
        return

    value = None

    if "AXFrame" in attr_names:
        error_code, attr_val = ApplicationServices.AXUIElementCopyAttributeValue(node, "AXFrame", None)
        rep = repr(attr_val)
        x_value = re.search(r"x:(-?[\d.]+)", rep)
        y_value = re.search(r"y:(-?[\d.]+)", rep)
        w_value = re.search(r"w:(-?[\d.]+)", rep)
        h_value = re.search(r"h:(-?[\d.]+)", rep)
        type_value = re.search(r"type\s?=\s?(\w+)", rep)
        value = {
            "x": float(x_value.group(1)) if x_value else None,
            "y": float(y_value.group(1)) if y_value else None,
            "w": float(w_value.group(1)) if w_value else None,
            "h": float(h_value.group(1)) if h_value else None,
            "type": type_value.group(1) if type_value else None,
        }

        if not any(v is None for v in value.values()):
            x_min = max(bbox[0], value["x"])
            x_max = min(bbox[2], value["x"] + value["w"])
            y_min = max(bbox[1], value["y"])
            y_max = min(bbox[3], value["y"] + value["h"])
            if x_min > x_max or y_min > y_max:
                return

    role = None
    text = None

    for attr_name, ns_key in reserved_keys.items():
        if attr_name not in attr_names:
            continue

        if value and attr_name == "AXFrame":
            bb = value
            if not any(v is None for v in bb.values()):
                attribute_dict["{{{:}}}screencoord".format(_accessibility_ns_map_macos["cp"])] = \
                    "({:d}, {:d})".format(int(bb["x"]), int(bb["y"]))
                attribute_dict["{{{:}}}size".format(_accessibility_ns_map_macos["cp"])] = \
                    "({:d}, {:d})".format(int(bb["w"]), int(bb["h"]))
            continue

        error_code, attr_val = ApplicationServices.AXUIElementCopyAttributeValue(node, attr_name, None)
        full_attr_name = f"{{{_accessibility_ns_map_macos[ns_key]}}}{attr_name}"

        if attr_name == "AXValue" and not text:
            text = str(attr_val)
            continue

        if attr_name == "AXRoleDescription":
            role = attr_val
            continue

        if not (isinstance(attr_val, ApplicationServices.AXUIElementRef)
                or isinstance(attr_val, (AppKit.NSArray, list))):
            if attr_val is not None:
                attribute_dict[full_attr_name] = str(attr_val)

    node_role_name = role.lower().replace(" ", "_") if role else "unknown_role"

    xml_node = lxml.etree.Element(
        node_role_name,
        attrib=attribute_dict,
        nsmap=_accessibility_ns_map_macos
    )

    if text is not None and len(text) > 0:
        xml_node.text = text

    if depth == MAX_DEPTH:
        logger.warning("Max depth reached")
        return xml_node

    import concurrent.futures
    future_to_child = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for attr_name, ns_key in reserved_keys.items():
            if attr_name not in attr_names:
                continue

            error_code, attr_val = ApplicationServices.AXUIElementCopyAttributeValue(node, attr_name, None)
            if isinstance(attr_val, ApplicationServices.AXUIElementRef):
                future_to_child.append(executor.submit(_create_axui_node, attr_val, nodes, depth + 1, bbox))
            elif isinstance(attr_val, (AppKit.NSArray, list)):
                for child in attr_val:
                    future_to_child.append(executor.submit(_create_axui_node, child, nodes, depth + 1, bbox))

        try:
            for future in concurrent.futures.as_completed(future_to_child):
                result = future.result()
                if result is not None:
                    xml_node.append(result)
        except Exception as e:
            logger.error(f"Exception occurred: {e}")

    return xml_node


@app.route("/accessibility", methods=["GET"])
def get_accessibility_tree():
    xml_node = lxml.etree.Element("desktop", nsmap=_accessibility_ns_map_macos)

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        foreground_windows = [
            win for win in Quartz.CGWindowListCopyWindowInfo(
                (Quartz.kCGWindowListExcludeDesktopElements |
                 Quartz.kCGWindowListOptionOnScreenOnly),
                Quartz.kCGNullWindowID
            ) if win["kCGWindowLayer"] == 0 and win["kCGWindowOwnerName"] != "Window Server"
        ]
        dock_info = [
            win for win in Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionAll,
                Quartz.kCGNullWindowID
            ) if win.get("kCGWindowName", None) == "Dock"
        ]

        futures = [
            executor.submit(_create_axui_node, wnd, None, 0)
            for wnd in foreground_windows + dock_info
        ]

        for future in concurrent.futures.as_completed(futures):
            xml_tree = future.result()
            if xml_tree is not None:
                xml_node.append(xml_tree)

    return jsonify({"AT": lxml.etree.tostring(xml_node, encoding="unicode")})


# ============================================================
# Screen size (macOS: CGMainDisplayID)
# ============================================================
@app.route('/screen_size', methods=['POST'])
def get_screen_size():
    import Quartz
    screen = Quartz.CGMainDisplayID()
    screen_width = Quartz.CGDisplayPixelsWide(screen)
    screen_height = Quartz.CGDisplayPixelsHigh(screen)
    return jsonify({"width": screen_width, "height": screen_height})


@app.route('/window_size', methods=['POST'])
def get_window_size():
    if 'app_class_name' in request.form:
        app_class_name = request.form['app_class_name']
    else:
        return jsonify({"error": "app_class_name is required"}), 400

    # Use NSWorkspace to find windows by app name
    apps = AppKit.NSWorkspace.sharedWorkspace().runningApplications()
    for app in apps:
        if app.localizedName() == app_class_name:
            pid = app.processIdentifier()
            # Get AXUIElement for the app
            app_element = ApplicationServices.AXUIElementCreateApplication(pid)
            error_code, windows_ref = ApplicationServices.AXUIElementCopyAttributeValue(
                app_element, ApplicationServices.kAXWindowsAttribute, None)
            if error_code or not windows_ref:
                continue
            for window_ref in windows_ref:
                error_code, axvalue = ApplicationServices.AXUIElementCopyAttributeValue(
                    window_ref, ApplicationServices.kAXPositionAttribute, None)
                if not error_code:
                    # Return first window found
                    return jsonify({"width": 800, "height": 600})
    return None


# ============================================================
# Terminal output (macOS - not implemented)
# ============================================================
@app.route('/terminal', methods=['GET'])
def get_terminal_output():
    return "Currently not implemented for macOS.", 500


# ============================================================
# Recording (macOS: screencapture + ffmpeg or avfoundation)
# ============================================================
@app.route('/start_recording', methods=['POST'])
def start_recording():
    return "Recording not yet implemented for macOS.", 501


@app.route('/end_recording', methods=['POST'])
def end_recording():
    return "Recording not yet implemented for macOS.", 501


# ============================================================
# Wallpaper (macOS: osascript)
# ============================================================
def _change_wallpaper_darwin(path: Path):
    subprocess.run(
        ["osascript", "-e", f'tell application "Finder" to set desktop picture to POSIX file "{path}"']
    )


# ============================================================
# Window management (macOS: pygetwindow or NSRunningApplication)
# ============================================================
def _activate_window_darwin(window_name: str, strict: bool):
    import pygetwindow as gw

    windows = gw.getWindowsWithTitle(window_name)
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

    window.unminimize()
    window.activate()
    return "Window activated successfully", 200


def _close_window_darwin(window_name: str):
    return "Currently not supported on macOS.", 500


# ============================================================
# Entry point
# ============================================================
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")
