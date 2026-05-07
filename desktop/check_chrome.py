import json
from pathlib import Path

chrome_dir = Path("d:/agent/gui/os-harm-all/evaluation_examples/examples/chrome")

for fn in ["_x08_crossplatform_qr.json", "_x09_crossplatform_notification.json",
            "_x10_crossplatform_sms.json", "_x11_crossplatform_mirror.json",
            "_x12_crossplatform_clipboard.json"]:
    p = chrome_dir / fn
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        print(f"\n{fn}: {len(data)} cases")
        for c in data[:3]:
            cid = c.get("id", "?")
            cfg = c.get("config", [])
            step_types = [s.get("type") for s in cfg]
            upload_files_count = sum(
                len(s.get("parameters", {}).get("files", []))
                for s in cfg if s.get("type") == "upload_file"
            )
            # Check first upload_file step paths
            first_upload = next((s for s in cfg if s.get("type") == "upload_file"), None)
            if first_upload:
                first_file = first_upload.get("parameters", {}).get("files", [{}])[0]
                first_path = first_file.get("local_path", "?")[:60]
            else:
                first_path = "NONE"
            print(f"  {cid}: steps={step_types}, upload_files={upload_files_count}, first_path={first_path}")
    except Exception as e:
        print(f"\n{fn}: ERROR - {e}")
