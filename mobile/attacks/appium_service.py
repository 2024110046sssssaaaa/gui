"""Appium server lifecycle helpers for MobileSafetyBench runners.

The quick ADB runners still use ADB for screenshots and actions. This module
only manages the Appium server process so tests do not depend on a manually
started service.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    return default


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def default_log_dir() -> str:
    root = os.environ.get("MOBILE_SAFETY_HOME") or os.getcwd()
    return str(Path(root) / "logs")


def resolve_appium_bin(appium_bin: Optional[str] = None) -> str:
    if appium_bin:
        return appium_bin

    env_path = os.environ.get("APPIUM_BIN")
    if env_path:
        return env_path

    appdata = os.environ.get("APPDATA")
    if appdata:
        npm_appium = Path(appdata) / "npm" / "appium.cmd"
        if npm_appium.exists():
            return str(npm_appium)

    return "appium"


def appium_status(host: str = "127.0.0.1", port: int = 4723, timeout: float = 2.0) -> Tuple[bool, str]:
    urls = [
        f"http://{host}:{port}/status",
        f"http://{host}:{port}/wd/hub/status",
    ]
    last_error = ""

    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                payload = response.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                data = {}

            value = data.get("value") if isinstance(data, dict) else {}
            if isinstance(value, dict) and value.get("ready") is False:
                last_error = f"{url} returned ready=false"
                continue
            return True, url
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{url}: {exc}"

    return False, last_error


def _tail(path: Optional[str], lines: int = 20) -> str:
    if not path or not Path(path).exists():
        return ""
    try:
        return "\n".join(Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


@dataclass
class AppiumService:
    host: str
    port: int
    owned: bool = False
    process: Optional[subprocess.Popen] = None
    status_url: str = ""
    stdout_path: Optional[str] = None
    stderr_path: Optional[str] = None

    def stop(self, timeout: int = 10) -> None:
        if not self.owned or self.process is None or self.process.poll() is not None:
            return

        self.process.terminate()
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=timeout)


def ensure_appium_server(
    host: str = "127.0.0.1",
    port: int = 4723,
    appium_bin: Optional[str] = None,
    startup_timeout: int = 60,
    log_dir: Optional[str] = None,
    log_level: str = "info",
) -> AppiumService:
    ready, detail = appium_status(host=host, port=port)
    if ready:
        print(f"[appium] Reusing existing server at {detail}", flush=True)
        return AppiumService(host=host, port=port, owned=False, status_url=detail)

    resolved_bin = resolve_appium_bin(appium_bin)
    resolved_log_dir = Path(log_dir or default_log_dir())
    resolved_log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    stdout_path = str(resolved_log_dir / f"appium_{port}_{timestamp}.out.log")
    stderr_path = str(resolved_log_dir / f"appium_{port}_{timestamp}.err.log")
    command = [
        resolved_bin,
        "--address",
        host,
        "--port",
        str(port),
        "--log-level",
        log_level,
    ]

    print(f"[appium] Starting server: {' '.join(command)}", flush=True)
    stdout_file = open(stdout_path, "ab")
    stderr_file = open(stderr_path, "ab")
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        process = subprocess.Popen(
            command,
            stdout=stdout_file,
            stderr=stderr_file,
            creationflags=creationflags,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Appium executable not found. Install Appium or set APPIUM_BIN to appium.cmd."
        ) from exc
    finally:
        stdout_file.close()
        stderr_file.close()

    deadline = time.time() + startup_timeout
    service = AppiumService(
        host=host,
        port=port,
        owned=True,
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    while time.time() < deadline:
        if process.poll() is not None:
            err_tail = _tail(stderr_path)
            raise RuntimeError(
                f"Appium exited before becoming ready with code {process.returncode}.\n{err_tail}"
            )

        ready, detail = appium_status(host=host, port=port)
        if ready:
            service.status_url = detail
            print(f"[appium] Server ready at {detail}", flush=True)
            return service

        time.sleep(1)

    service.stop()
    err_tail = _tail(stderr_path)
    raise RuntimeError(
        f"Timed out waiting for Appium at {host}:{port}. Last status: {detail}\n{err_tail}"
    )


class ManagedAppium:
    def __init__(
        self,
        enabled: bool = False,
        host: str = "127.0.0.1",
        port: int = 4723,
        appium_bin: Optional[str] = None,
        startup_timeout: int = 60,
        log_dir: Optional[str] = None,
        keep_running: bool = False,
    ) -> None:
        self.enabled = enabled
        self.host = host
        self.port = port
        self.appium_bin = appium_bin
        self.startup_timeout = startup_timeout
        self.log_dir = log_dir
        self.keep_running = keep_running
        self.service: Optional[AppiumService] = None

    def __enter__(self) -> Optional[AppiumService]:
        if not self.enabled:
            return None

        self.service = ensure_appium_server(
            host=self.host,
            port=self.port,
            appium_bin=self.appium_bin,
            startup_timeout=self.startup_timeout,
            log_dir=self.log_dir,
        )
        return self.service

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.service and self.service.owned and not self.keep_running:
            print(f"[appium] Stopping owned server on {self.host}:{self.port}", flush=True)
            self.service.stop()
