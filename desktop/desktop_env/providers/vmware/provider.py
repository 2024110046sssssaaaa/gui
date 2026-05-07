import logging
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

from desktop_env.providers.base import Provider

logger = logging.getLogger("desktopenv.providers.vmware.VMwareProvider")
logger.setLevel(logging.INFO)

WAIT_TIME = 3

# Server files that need to be deployed to the VM
SERVER_FILES = [
    "_start_server.py",
    "common.py",
    "main_linux.py",
    "pyxcursor.py",
    "pyxcursor/__init__.py",
]


def get_vmrun_type(return_list=False):
    if platform.system() == 'Windows' or platform.system() == 'Linux':
        if return_list:
            return ['-T', 'ws']
        else:
            return '-T ws'
    elif platform.system() == 'Darwin':  # Darwin is the system name for macOS
        if return_list:
            return ['-T', 'fusion']
        else:
            return '-T fusion'
    else:
        raise Exception("Unsupported operating system")


class VMwareProvider(Provider):
    @staticmethod
    def _execute_command(command: list, return_output=False):
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )

        return process.communicate()[0].strip() if return_output else None

    def start_emulator(self, path_to_vm: str, headless: bool, os_type: str):
        print("Starting VMware VM...")
        logger.info("Starting VMware VM...")

        while True:
            try:
                output = subprocess.check_output(f"vmrun {get_vmrun_type()} list", shell=True, stderr=subprocess.STDOUT)
                output = output.decode()
                output = output.splitlines()
                normalized_path_to_vm = os.path.abspath(os.path.normpath(path_to_vm)).lower()

                if any(os.path.abspath(os.path.normpath(line)).lower() == normalized_path_to_vm for line in output):
                    logger.info("VM is running.")
                    break
                else:
                    logger.info("Starting VM...")
                    _command = ["vmrun"] + get_vmrun_type(return_list=True) + ["start", path_to_vm]
                    if headless:
                        _command.append("nogui")
                    VMwareProvider._execute_command(_command)
                    time.sleep(WAIT_TIME)

            except subprocess.CalledProcessError as e:
                logger.error(f"Error executing command: {e.output.decode().strip()}")

    def get_ip_address(self, path_to_vm: str) -> str:
        logger.info("Getting VMware VM IP address...")
        while True:
            try:
                output = VMwareProvider._execute_command(
                    ["vmrun"] + get_vmrun_type(return_list=True) + ["getGuestIPAddress", path_to_vm, "-wait"],
                    return_output=True
                )
                logger.info(f"VMware VM IP address: {output}")
                return output
            except Exception as e:
                logger.error(e)
                time.sleep(WAIT_TIME)
                logger.info("Retrying to get VMware VM IP address...")

    def save_state(self, path_to_vm: str, snapshot_name: str):
        logger.info("Saving VMware VM state...")
        VMwareProvider._execute_command(
            ["vmrun"] + get_vmrun_type(return_list=True) + ["snapshot", path_to_vm, snapshot_name])
        time.sleep(WAIT_TIME)  # Wait for the VM to save

    def revert_to_snapshot(self, path_to_vm: str, snapshot_name: str):
        logger.info(f"Reverting VMware VM to snapshot: {snapshot_name}...")
        VMwareProvider._execute_command(
            ["vmrun"] + get_vmrun_type(return_list=True) + ["revertToSnapshot", path_to_vm, snapshot_name])
        time.sleep(WAIT_TIME)  # Wait for the VM to revert
        return path_to_vm

    def stop_emulator(self, path_to_vm: str):
        logger.info("Stopping VMware VM...")
        VMwareProvider._execute_command(["vmrun"] + get_vmrun_type(return_list=True) + ["stop", path_to_vm])
        time.sleep(WAIT_TIME)  # Wait for the VM to stop

    def get_server_dir(self) -> Path:
        server_dir = Path(__file__).parent.parent.parent / "server"
        return server_dir

    def _bash_in_guest(self, path_to_vm: str, command: str, timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["vmrun", "-T", "ws", "-gu", "user", "-gp", "password",
             "runProgramInGuest", path_to_vm, "-activeWindow",
             "/bin/bash", "-c", command],
            capture_output=True, text=True, timeout=timeout
        )

    def _upload_file(self, path_to_vm: str, src: str, dst: str) -> bool:
        r = subprocess.run(
            ["vmrun", "-T", "ws", "-gu", "user", "-gp", "password",
             "copyFileFromHostToGuest", path_to_vm, src, dst],
            capture_output=True, text=True, timeout=15
        )
        return r.returncode == 0

    def _read_guest_file(self, path_to_vm: str, guest_path: str, local_path: str) -> str:
        subprocess.run(
            ["vmrun", "-T", "ws", "-gu", "user", "-gp", "password",
             "copyFileFromGuestToHost", path_to_vm, guest_path, local_path],
            capture_output=True, text=True, timeout=15
        )
        for enc in ["utf-8", "latin-1"]:
            try:
                with open(local_path, "r", encoding=enc) as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def deploy_server(self, path_to_vm: str):
        logger.info("Deploying server files to VM...")
        server_dir = self.get_server_dir()

        uploaded = []
        failed = []

        for fname in SERVER_FILES:
            src = server_dir / fname
            if not src.exists():
                failed.append(f"{fname} (not found: {src})")
                continue
            dst = f"/home/user/{fname}"
            if self._upload_file(path_to_vm, str(src), dst):
                logger.info(f"  Uploaded: {fname}")
                uploaded.append(fname)
            else:
                failed.append(f"{fname} (upload failed)")
                logger.error(f"  Failed to upload: {fname}")

        if failed:
            logger.warning(f"Some files failed: {failed}")

        if not uploaded:
            raise RuntimeError("No server files were uploaded successfully!")

        return uploaded

    def install_deps(self, path_to_vm: str):
        logger.info("Installing Python dependencies in VM...")
        r = self._bash_in_guest(
            path_to_vm,
            "pip install flask pyautogui lxml Pillow requests python-xlib pyyaml numpy "
            "-i https://pypi.tuna.tsinghua.edu.cn/simple "
            "> /tmp/pip_deps.log 2>&1; echo EXIT:$? >> /tmp/pip_deps.log",
            timeout=300
        )
        if r.returncode != 0:
            logger.warning(f"pip install returned {r.returncode}")

    def start_server(self, path_to_vm: str, vm_ip: str = None) -> bool:
        logger.info("Starting Flask server in VM...")
        if vm_ip is None:
            vm_ip = "192.168.144.128"

        r = self._bash_in_guest(
            path_to_vm,
            "pkill -f '_start_server' 2>/dev/null; sleep 2",
            timeout=15
        )

        runner_script = (
            "#!/bin/bash\n"
            "export DISPLAY=:0\n"
            "touch /home/user/.Xauthority\n"
            "cd /home/user\n"
            "nohup python3 -u /home/user/_start_server.py > /home/user/flask_startup.log 2>&1 &\n"
            "echo \"Flask PID=$!\"\n"
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, encoding='utf-8') as f:
            f.write(runner_script)
            tmp_script = f.name

        try:
            self._upload_file(path_to_vm, tmp_script, "/tmp/__start_flask.sh")
        finally:
            try:
                os.unlink(tmp_script)
            except Exception:
                pass

        r = self._bash_in_guest(path_to_vm, "bash /tmp/__start_flask.sh", timeout=15)
        logger.info(f"Start server command rc={r.returncode}")

        for attempt in range(3):
            time.sleep(5)
            try:
                import requests as _req
                resp = _req.get(f"http://{vm_ip}:5000/screenshot", timeout=5)
                if resp.status_code == 200:
                    logger.info(f"Flask server is running! screenshot={len(resp.content)} bytes")
                    return True
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}: server not ready yet - {e}")

        log = self._read_guest_file(path_to_vm, "/home/user/flask_startup.log",
                                     str(self.get_server_dir() / "__startup.log"))
        logger.warning(f"Flask startup log:\n{log[-1000:]}")
        return False

    def ensure_server_running(self, path_to_vm: str, vm_ip: str = None):
        if vm_ip is None:
            vm_ip = "192.168.144.128"
        try:
            import requests as _req
            resp = _req.get(f"http://{vm_ip}:5000/screenshot", timeout=5)
            if resp.status_code == 200:
                logger.info("Server already running.")
                return
        except Exception:
            pass

        logger.info("Server not responding, will restart...")
        self.start_server(path_to_vm, vm_ip)
