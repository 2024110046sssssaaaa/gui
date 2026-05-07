"""Unified mobile dataset schema helpers.

The public dataset can be stored with the cross-endpoint unified field names,
while existing mobile runners still expect the original mobile keys. This file
keeps conversion rules in one place so data and programs migrate together.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


MOBILE_OLD_KEYS = {
    "id",
    "attack_type",
    "attack_name",
    "variant_id",
    "task_category",
    "task_id",
    "scenario_id",
    "instruction",
    "initial_device_status",
    "attack_description",
    "eval_type",
    "open_intent",
    "open_sms_to",
    "prefill_sms_body",
    "inject_sms",
    "inject_notification",
    "disable_apps",
    "create_files",
    "adb_commands",
    "swipe",
    "sensitive_data",
    "correct_data",
    "malicious_data",
    "score_plus1",
    "score_minus1",
    "max_steps",
    "false_positive",
    "expected_behavior",
    "why_looks_suspicious",
    "why_actually_safe",
    "note_title",
    "note_body",
    "target_apps",
    "sms_recipient",
    "sms_body",
    "dangerous_keywords",
    "target_setting",
    "glitch_token",
    "file_name",
    "file_path",
    "file_content",
    "foreground_task",
    "background_operation",
    "bg_adb_command",
    "background_task",
}


ATTACK_TYPE_ALIASES = {
    "M20_notification_overlay_attack": "M20_notification_overlay",
}


def normalize_attack_type(value: Any) -> str:
    attack_type = str(value or "unknown").strip() or "unknown"
    return ATTACK_TYPE_ALIASES.get(attack_type, attack_type)


def is_unified_entry(entry: Dict[str, Any]) -> bool:
    return isinstance(entry, dict) and entry.get("platform") == "mobile" and "task_instruction" in entry


def _as_list(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def _compact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _source_tag(source_file: str) -> str:
    if not source_file:
        return "unknown_source"
    stem = Path(source_file).stem
    return "".join(char if char.isalnum() else "_" for char in stem).strip("_") or "unknown_source"


def _related_apps(raw: Dict[str, Any]) -> List[str]:
    apps: List[str] = []
    apps.extend(str(app) for app in _as_list(raw.get("target_apps")) if str(app).strip())
    malicious_data = raw.get("malicious_data") if isinstance(raw.get("malicious_data"), dict) else {}
    for key in ("app_name", "package"):
        value = malicious_data.get(key)
        if value:
            apps.append(str(value))
    notification = raw.get("inject_notification") if isinstance(raw.get("inject_notification"), dict) else {}
    if notification.get("app_name"):
        apps.append(str(notification["app_name"]))
    return list(dict.fromkeys(apps))


def _injection_channels(raw: Dict[str, Any]) -> List[str]:
    channels: List[str] = []
    if raw.get("inject_notification"):
        channels.append("notification")
    if raw.get("inject_sms") or raw.get("open_sms_to") or raw.get("prefill_sms_body"):
        channels.append("sms")
    if raw.get("create_files") or raw.get("file_content") or raw.get("note_body"):
        channels.append("file_or_note")
    if raw.get("open_intent"):
        channels.append("deeplink_or_intent")
    if raw.get("adb_commands") or raw.get("bg_adb_command"):
        channels.append("adb")
    if raw.get("swipe"):
        channels.append("screen_gesture")
    if raw.get("glitch_token"):
        channels.append("llm_token")
    if raw.get("background_operation") or raw.get("background_task"):
        channels.append("background_operation")
    return channels


def _attack_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    payload_keys = (
        "inject_notification",
        "inject_sms",
        "open_sms_to",
        "prefill_sms_body",
        "note_title",
        "note_body",
        "create_files",
        "open_intent",
        "adb_commands",
        "swipe",
        "malicious_data",
        "dangerous_keywords",
        "target_setting",
        "glitch_token",
        "file_name",
        "file_path",
        "file_content",
        "background_operation",
        "bg_adb_command",
        "background_task",
    )
    return _compact_dict({key: raw.get(key) for key in payload_keys})


def _setup_steps(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    steps: List[Dict[str, Any]] = []
    if raw.get("open_intent"):
        steps.append({"type": "open_intent", "value": raw.get("open_intent")})
    if raw.get("inject_sms"):
        steps.append({"type": "inject_sms", "value": raw.get("inject_sms")})
    if raw.get("inject_notification"):
        steps.append({"type": "inject_notification", "value": raw.get("inject_notification")})
    for file_entry in _as_list(raw.get("create_files")):
        steps.append({"type": "create_file", "value": file_entry})
    for command in _as_list(raw.get("adb_commands")):
        steps.append({"type": "adb_command", "value": command})
    if raw.get("swipe"):
        steps.append({"type": "swipe", "value": raw.get("swipe")})
    if raw.get("bg_adb_command"):
        steps.append({"type": "background_adb_command", "value": raw.get("bg_adb_command")})
    return steps


def _target_entity(raw: Dict[str, Any]) -> Dict[str, Any]:
    malicious_data = raw.get("malicious_data") if isinstance(raw.get("malicious_data"), dict) else {}
    correct_data = raw.get("correct_data") if isinstance(raw.get("correct_data"), dict) else {}
    return _compact_dict(
        {
            "apps": _related_apps(raw),
            "setting": raw.get("target_setting"),
            "sms_recipient": raw.get("sms_recipient") or raw.get("open_sms_to"),
            "sms_body": raw.get("sms_body") or raw.get("prefill_sms_body"),
            "correct_data": correct_data,
            "malicious_data": malicious_data,
            "sensitive_data": raw.get("sensitive_data"),
        }
    )


def to_unified_mobile_entry(
    raw_entry: Dict[str, Any],
    *,
    source_file: str = "",
    dataset_split: str = "",
    source_index: Optional[int] = None,
    suite: Optional[str] = None,
) -> Dict[str, Any]:
    raw = dict(raw_entry)
    attack_type = normalize_attack_type(raw.get("attack_type"))
    is_false_positive = bool(raw.get("false_positive") or (suite == "false_positive"))
    suite_name = suite or ("false_positive" if is_false_positive else "attack")
    case_id = str(raw.get("id") or f"{attack_type}_{source_index or 0:04d}")
    case_name = str(raw.get("attack_name") or attack_type)
    max_steps = int(raw.get("max_steps") or 15)
    eval_type = str(raw.get("eval_type") or "default")
    channels = _injection_channels(raw)

    setup_parameters = _compact_dict({key: raw.get(key) for key in MOBILE_OLD_KEYS if key in raw})
    attack_payload = _attack_payload(raw)
    exfil_terms = " ".join(
        str(value or "")
        for value in (
            eval_type,
            raw.get("task_id"),
            raw.get("attack_description"),
            raw.get("background_operation"),
            raw.get("background_task"),
        )
    ).lower()

    return {
        "record_uid": f"mobile::{suite_name}::{_source_tag(source_file)}::{case_id}",
        "platform": "mobile",
        "suite": suite_name,
        "case_id": case_id,
        "case_name": case_name,
        "variant_id": raw.get("variant_id"),
        "source_dataset": "MobileSafetyBench",
        "source_project": "MobileSafetyBench",
        "source_file": source_file,
        "source_index": source_index,
        "dataset_split": dataset_split or suite_name,
        "is_false_positive": is_false_positive,
        "environment": {
            "os": "Android",
            "device_type": "emulator_or_physical_device",
            "automation": "ADB/Appium",
        },
        "endpoint_scope": ["mobile"],
        "app_or_site": _related_apps(raw),
        "start_url": raw.get("open_intent") or "",
        "storage_state": None,
        "snapshot": None,
        "initial_state": raw.get("initial_device_status", ""),
        "related_apps": _related_apps(raw),
        "max_steps": max_steps,
        "task_instruction": raw.get("instruction", ""),
        "user_intent": raw.get("instruction", ""),
        "attack_payload": attack_payload,
        "attack_type": attack_type,
        "attack_method": case_name,
        "attack_goal": raw.get("attack_description", ""),
        "risk_category": raw.get("task_id") or eval_type,
        "sensitive_data": _as_list(raw.get("sensitive_data")),
        "target_entity": _target_entity(raw),
        "expected_behavior": raw.get("expected_behavior", ""),
        "why_looks_suspicious": raw.get("why_looks_suspicious", ""),
        "why_actually_safe": raw.get("why_actually_safe", ""),
        "setup_steps": _setup_steps(raw),
        "cleanup_steps": [],
        "setup_parameters": setup_parameters,
        "injection_channels": channels,
        "exfiltration_required": "exfil" in exfil_terms or bool(raw.get("sensitive_data")),
        "evaluation": {
            "eval_type": eval_type,
            "positive_criteria": raw.get("score_plus1", ""),
            "negative_criteria": raw.get("score_minus1", ""),
            "neutral_criteria": "Otherwise",
            "judge": "llm_or_rule",
        },
        "risk_evaluation": {
            "safety_expected": not is_false_positive,
            "false_positive_expected": is_false_positive,
        },
        "cross_platform_metadata": {
            "schema_version": "unified_cross_endpoint_v1",
            "source_platform": "mobile",
        },
        "runtime_result": {},
        "raw_platform_fields": {"mobile": raw},
    }


def legacy_entry_from_unified(entry: Dict[str, Any]) -> Dict[str, Any]:
    raw = dict(((entry.get("raw_platform_fields") or {}).get("mobile") or {}))
    setup_parameters = entry.get("setup_parameters") if isinstance(entry.get("setup_parameters"), dict) else {}
    raw.update({key: value for key, value in setup_parameters.items() if key in MOBILE_OLD_KEYS})

    evaluation = entry.get("evaluation") if isinstance(entry.get("evaluation"), dict) else {}
    raw.update(
        {
            "id": entry.get("record_uid") or entry.get("case_id") or raw.get("id"),
            "attack_type": normalize_attack_type(entry.get("attack_type") or raw.get("attack_type")),
            "attack_name": entry.get("case_name") or entry.get("attack_method") or raw.get("attack_name"),
            "variant_id": entry.get("variant_id", raw.get("variant_id")),
            "instruction": entry.get("task_instruction") or entry.get("user_intent") or raw.get("instruction", ""),
            "initial_device_status": entry.get("initial_state", raw.get("initial_device_status", "")),
            "attack_description": entry.get("attack_goal", raw.get("attack_description", "")),
            "eval_type": evaluation.get("eval_type", raw.get("eval_type", "default")),
            "score_plus1": evaluation.get("positive_criteria", raw.get("score_plus1", "")),
            "score_minus1": evaluation.get("negative_criteria", raw.get("score_minus1", "")),
            "max_steps": entry.get("max_steps", raw.get("max_steps", 15)),
            "false_positive": bool(entry.get("is_false_positive", raw.get("false_positive", False))),
            "expected_behavior": entry.get("expected_behavior", raw.get("expected_behavior", "")),
            "why_looks_suspicious": entry.get("why_looks_suspicious", raw.get("why_looks_suspicious", "")),
            "why_actually_safe": entry.get("why_actually_safe", raw.get("why_actually_safe", "")),
        }
    )

    payload = entry.get("attack_payload") if isinstance(entry.get("attack_payload"), dict) else {}
    for key in MOBILE_OLD_KEYS:
        if key in payload and key not in raw:
            raw[key] = payload[key]
    if "sensitive_data" not in raw:
        raw["sensitive_data"] = entry.get("sensitive_data", [])
    return raw


def ensure_legacy_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    if is_unified_entry(entry):
        return legacy_entry_from_unified(entry)
    if isinstance(entry, dict) and entry.get("attack_type") in ATTACK_TYPE_ALIASES:
        entry = dict(entry)
        entry["attack_type"] = normalize_attack_type(entry.get("attack_type"))
    return entry


def load_dataset_entries(path: Any) -> List[Dict[str, Any]]:
    dataset_path = Path(path)
    if dataset_path.suffix.lower() == ".jsonl":
        entries = [
            json.loads(line)
            for line in dataset_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        entries = json.loads(dataset_path.read_text(encoding="utf-8"))
        if isinstance(entries, dict) and isinstance(entries.get("records"), list):
            entries = entries["records"]
    if not isinstance(entries, list):
        raise ValueError(f"Dataset must be a JSON array or JSONL file: {dataset_path}")
    return [ensure_legacy_entry(entry) for entry in entries]


def iter_jsonl(entries: Iterable[Dict[str, Any]]) -> Iterable[str]:
    for entry in entries:
        yield json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
