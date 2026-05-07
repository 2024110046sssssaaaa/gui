# MobileSafetyBench Project Inventory

This document separates the files that are needed for current mobile safety
experiments from historical scripts, debug artifacts, and generated results.

Last updated: 2026-05-06

## Recommended Entry Point

Use this launcher for new experiments:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_mobile_guard_portable.ps1
```

Why this is the preferred path:

- It supports both attack and false-positive evaluation.
- It sets the mobile guard defense prompt and related environment variables.
- It starts or reuses Appium once before the dataset loop.
- It writes results into timestamped `result_*` directories.
- It keeps child runners from restarting Appium for every dataset.

Direct runner usage is still supported:

```powershell
python attacks\quick_test_adb.py --dataset <attack_simpletest_json>
python attacks\quick_test_adb_fp.py --dataset <false_positive_json>
```

Direct runners now manage Appium by default. Use `--no-manage-appium` only when
another wrapper already owns the Appium service.

## Required External Programs

The current Windows workflow needs:

- Python with packages from `requirements.txt`.
- Android SDK, especially `adb` and emulator tools. The current scripts default to `D:\sdk`.
- A running Android emulator or connected Android device.
- Node.js/npm if Appium is installed via npm.
- Appium v2/v3.
- Appium `uiautomator2` driver.
- Model API credentials for the selected backend.

Useful environment variables:

```powershell
$env:MOBILE_SAFETY_HOME = "D:\datasets\MobileSafetyBench"
$env:ANDROID_HOME = "D:\sdk"
$env:ANDROID_SDK_ROOT = "D:\sdk"
$env:APPIUM_BIN = "C:\Users\<you>\AppData\Roaming\npm\appium.cmd"
$env:OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:THIRD_PARTY_PROXY_BASE_URL = "https://api.example.com/v1/chat/completions"
$env:THIRD_PARTY_PROXY_API_KEY = "<key>"
```

Do not commit real API keys.

## Core Runtime Files

These are the files currently needed for the maintained test flow.

| Role | Path | Notes |
|---|---|---|
| Main launcher | `scripts/run_mobile_guard_portable.ps1` | Recommended entry for attack/fp batches. |
| Attack runner | `attacks/quick_test_adb.py` | ADB screenshots/actions, model calls, scoring, Appium service lifecycle. |
| False-positive runner | `attacks/quick_test_adb_fp.py` | FP execution/scoring, LLM judge, Appium service lifecycle. |
| Appium manager | `attacks/appium_service.py` | Starts/reuses/stops Appium safely. |
| Shared attack utilities | `attacks/_attack_runner.py` | ADB path, API base URL helpers, legacy batch compatibility. |
| Task initialization | `attacks/batch_runner_v2.py` | Current task setup and ADB evaluator helpers. |
| FP judge | `attacks/llm_judge_fp.py` | LLM-based false-positive judging. |
| Defense prompt | `mobile_safety/prompt/asb_mobile_guard_defense_prompt.json` | Default ASB-style mobile guard prompt. |
| Alternative defense prompt | `mobile_safety/prompt/asb_sandwich_mobile_defense_prompt.json` | Sandwich variant. |
| Alternative defense prompt | `mobile_safety/prompt/wasp_mobile_defense_prompt.json` | WASP-style variant. |
| Original framework modules | `mobile_safety/` | Agents, components, evaluators, prompts, tasks. |
| Environment assets | `asset/environments/` | APKs, init scripts, files, wallpapers, emulator resources. |

## Active Dataset Sets

The current portable attack mode discovers `*_simpletest.json` under `attacks/`
and excludes false-positive folders. Current total:

- Attack simpletest files: 14
- Attack simpletest entries: 280

The current false-positive simplified set is under `attacks/false_positive_simple`.
Current total:

- False-positive simple files: 10
- False-positive simple entries: 200

The full false-positive set is under `attacks/false_positive`.
Current total:

- False-positive full files: 10
- False-positive full entries: 500

Machine-readable inventory:

- `docs/dataset_inventory.csv`

## Active Attack Simpletest Files

| Attack | Path | Count |
|---|---|---:|
| M07 | `attacks/1_visual_perception_attacks/M07_notification_injection/attack_data_enhanced_20260310_215949_v2_simpletest.json` | 20 |
| M08 | `attacks/2_environment_content_injection/M08_screen_text_injection/M08-diverse-attack_simpletest.json` | 20 |
| M09 | `attacks/2_environment_content_injection/M09_view_tree_interference/M09-diverse-attack_simpletest.json` | 20 |
| M10 | `attacks/3_direct_malicious_commands/M10_mobile_prompt_injection/M10-diverse-attack_simpletest.json` | 20 |
| M10-v2 | `attacks/3_direct_malicious_commands/M10_mobile_prompt_injection/M10-diverse-attack-v2_simpletest.json` | 20 |
| M11 | `attacks/3_direct_malicious_commands/M11_privacy_risk_operations/M11-100-test1/M11-diverse-attack_simpletest.json` | 20 |
| M12 | `attacks/3_direct_malicious_commands/M12_harmful_content_generation/M12-workplace-v4_simpletest.json` | 20 |
| M15 | `attacks/4_llm_reasoning_attacks/M15_malicious_instruction_exploitation/M15-diverse-attack_simpletest.json` | 20 |
| M16 | `attacks/4_llm_reasoning_attacks/M16_glitch_token_attack/M16-diverse-attack_simpletest.json` | 20 |
| M16-v2 | `attacks/4_llm_reasoning_attacks/M16_glitch_token_attack/M16-diverse-attack-v2_simpletest.json` | 20 |
| M13 | `attacks/5_system_exploitation/M13_deeplink_forgery/M13-diverse-attack_simpletest.json` | 20 |
| M20-v2 | `attacks/5_system_exploitation/M20_notification_overlay_attack/M20-diverse-attack-v2_simpletest.json` | 20 |
| M20-enhanced | `attacks/5_system_exploitation/M20_notification_overlay_attack/M20-diverse-attack-v2-enhanced_simpletest.json` | 20 |
| M21 | `attacks/5_system_exploitation/M21_background_attack/M21-diverse-attack_simpletest.json` | 20 |

## Active False-Positive Files

Simplified false positives:

| Folder | Files | Count per file | Total |
|---|---:|---:|---:|
| `attacks/false_positive_simple` | 10 | 20 | 200 |

Full false positives:

| Folder | Files | Count per file | Total |
|---|---:|---:|---:|
| `attacks/false_positive` | 10 | 50 | 500 |

Current false-positive attack ids:

- M07
- M08
- M09
- M10
- M11
- M12
- M15
- M16
- M20
- M21

## Raw Or Auxiliary Attack Data

Non-`*_simpletest.json` attack files are raw, full, older, or auxiliary sources.
They are useful for dataset construction and ablation, but they are not the
default portable evaluation target.

Important examples:

| Path | Count | Use |
|---|---:|---|
| `attacks/4_llm_reasoning_attacks/M16_glitch_token_attack/M16_attack_data_200.jsonl` | 200 | Exported JSONL subset for M16. |
| `attacks/4_llm_reasoning_attacks/M16_glitch_token_attack/M16-diverse-attack.json` | 100 | Raw M16 source. |
| `attacks/4_llm_reasoning_attacks/M16_glitch_token_attack/M16-diverse-attack-v2.json` | 100 | Raw M16 v2 source. |
| `attacks/3_direct_malicious_commands/M12_harmful_content_generation/M12-workplace-v4_new.json` | 200 | Revised M12 source. |
| `attacks/5_system_exploitation/M20_notification_overlay_attack/M20-diverse-attack-v2-enhanced.json` | 100 | Enhanced M20 source. |

See `docs/dataset_inventory.csv` for the full file-by-file inventory.

## Original MobileSafetyBench Assets

Keep these when reproducing emulator setup or original benchmark behavior:

| Path | Purpose |
|---|---|
| `mobile_safety/tasks/tasks.json` | Original task pool, 260 entries. |
| `mobile_safety/tasks/ui_spoofing_attacks.json` | UI spoofing task data, 12 entries. |
| `mobile_safety/prompt/` | Base prompts, defense prompts, safety/helpful prompt variants. |
| `mobile_safety/component/adb.py` | ADB helper code. |
| `mobile_safety/component/appium.py` | Original Appium driver helper. |
| `asset/environments/resource/apks/` | Joplin, SimpleCalendarPro, overlay APKs. |
| `asset/environments/script/` | Original shell setup scripts for emulator resources. |
| `asset/environments/resource/files/` | Prepared files used by tasks. |
| `asset/environments/resource/base64/` | Image/file resources encoded for task setup. |

APK inventory:

| APK | Notes |
|---|---|
| `asset/environments/resource/apks/Joplin.apk` | Notes app used by tasks. |
| `asset/environments/resource/apks/SimpleCalendarPro.apk` | Calendar app used by tasks. |
| `asset/environments/resource/apks/prompt_injection_overlay.apk` | Overlay/injection helper APK. |
| `asset/environments/resource/apks/transparent_overlay_attack.apk` | Transparent overlay helper APK. |
| `asset/environments/resource/apks/ui_overlay_attack.apk` | UI overlay helper APK. |

## Result And Log Outputs

Generated outputs should be treated as experiment artifacts, not source data.

| Pattern | Meaning |
|---|---|
| `logs/` | Runtime logs, screenshots, Appium logs. Current folder is large. |
| `result_*` | Model/test run outputs. |
| `qwen_*` | Qwen-specific run outputs. |
| `qianwen_*` | Older Qwen/DashScope run outputs. |
| `result_summary/` | Summaries derived from result folders. |
| `appendix_*.json` | Paper appendix sample/log selections. |
| `project_prompt_fields_only.*` | Prompt extraction artifacts. |
| `project_prompts_dump.md` | Prompt dump artifact. |

## Legacy Or Debug Files

The root directory contains many one-off files that are useful historically but
should not be the default experiment path:

- `debug_*.py`, `debug_*.txt`
- `test_*.py`, `test_*.log`
- `demo_*.py`
- `run_qwen_*`, `run_transparent_*`, `run_single_attack_demo.py`
- root-level screenshots such as `temp_screen.png`, `joplin_screen*.png`
- old setup helpers such as `auto_setup_avd.ps1`, `setup_env*.ps1`, `start_appium*.ps1`

Do not delete these without archiving; some may encode useful troubleshooting
knowledge.

## Suggested Future Cleanup

No files were moved during this inventory pass. A safe cleanup plan would be:

1. Keep source/runtime directories in place: `attacks/`, `mobile_safety/`, `asset/`, `scripts/`, `docs/`.
2. Move generated result folders into `archive/results/`.
3. Move debug logs/screenshots into `archive/debug_artifacts/`.
4. Move root one-off demo/test scripts into `archive/legacy_scripts/`.
5. Keep `scripts/run_mobile_guard_portable.ps1` as the only recommended new-run launcher.
6. Add a small `scripts/check_environment.ps1` later to validate Python, adb, Appium, emulator, and API envs before running.

## Typical Commands

Attack mode:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_mobile_guard_portable.ps1 `
  -Mode attack `
  -Model "qwen-vl-max-latest" `
  -AttackSimpletestOnly `
  -Start 0 `
  -Count 10 `
  -MaxSteps 8 `
  -AdbPort 5554
```

False-positive mode:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_mobile_guard_portable.ps1 `
  -Mode fp `
  -Model "qwen-vl-max-latest" `
  -First10FalsePositiveSimple `
  -Start 0 `
  -Count 10 `
  -MaxSteps 8 `
  -ApiTimeout 90 `
  -AdbPort 5554
```

Use a custom defense prompt:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_mobile_guard_portable.ps1 `
  -Mode attack `
  -DefensePrompt "D:\datasets\MobileSafetyBench\mobile_safety\prompt\wasp_mobile_defense_prompt.json"
```
