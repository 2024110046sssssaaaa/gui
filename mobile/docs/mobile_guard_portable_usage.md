# Mobile Guard Portable Usage

This file explains how to run the ASB-style mobile defense framework on another Windows machine without reusing the machine-specific batch scripts in this repository.

Main portable launcher:

- [run_mobile_guard_portable.ps1](D:/datasets/MobileSafetyBench/scripts/run_mobile_guard_portable.ps1)

## What this launcher does

It sets the same defense framework used in our recent experiments:

- defense prompt: `mobile_safety/prompt/asb_mobile_guard_defense_prompt.json`
- guard level: `strict`
- metadata-aware blocking: disabled by default with `MOBILE_SAFETY_GUARD_USE_TASK_METADATA=0`
- Appium service lifecycle: start or reuse Appium before the dataset loop, and stop only the Appium process started by this launcher
- child runners keep Appium management disabled in portable mode, so the service is not restarted for every dataset
- runner:
  - attack: `attacks/quick_test_adb.py`
  - false positive: `attacks/quick_test_adb_fp.py`

## Minimum requirements

The other machine should have:

1. This repository with the updated files.
2. Python environment that can run the MobileSafetyBench scripts.
3. Android SDK / `adb`.
4. Appium v2/v3 with the `uiautomator2` driver installed.
5. A running emulator or connected Android device.
6. Model API credentials.

## Recommended environment variables

If you use an OpenAI-compatible proxy:

```powershell
$env:THIRD_PARTY_PROXY_BASE_URL = "https://api.example.com/v1/chat/completions"
$env:THIRD_PARTY_PROXY_API_KEY = "your_api_key"
$env:OPENAI_COMPATIBLE_FORCE_RAW_AUTH = "1"
```

If you use DashScope-compatible OpenAI API:

```powershell
$env:OPENAI_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:DASHSCOPE_API_KEY = ""
```

## False-positive test example

Run 100 false-positive samples, that is the first 10 entries from each dataset under `attacks/false_positive_simple`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_mobile_guard_portable.ps1 `
  -Mode fp `
  -Model "gemini-3-pro-preview" `
  -PythonPath "D:\ANACONDA\python.exe" `
  -ProjectRoot "D:\datasets\MobileSafetyBench" `
  -First10FalsePositiveSimple `
  -Start 0 `
  -Count 10 `
  -MaxSteps 8 `
  -ApiTimeout 90 `
  -AdbPort 5554 `
  -ThirdPartyProxyBaseUrl "https://api.example.com/v1/chat/completions" `
  -ThirdPartyProxyApiKey "your_api_key"
```

## Attack test example

Run attack `*_simpletest.json` datasets with the same defense:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_mobile_guard_portable.ps1 `
  -Mode attack `
  -Model "qwen-vl-max-latest" `
  -PythonPath "D:\ANACONDA\python.exe" `
  -ProjectRoot "D:\datasets\MobileSafetyBench" `
  -AttackSimpletestOnly `
  -Start 10 `
  -Count 10 `
  -MaxSteps 8 `
  -AdbPort 5554 `
  -OpenAIBaseUrl "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

## Important options

- `-Mode fp`: run false-positive evaluation.
- `-Mode attack`: run attack simpletest evaluation.
- `-First10FalsePositiveSimple`: use `attacks/false_positive_simple`.
- `-AttackSimpletestOnly`: acknowledge attack mode is intended for `*_simpletest.json`.
- `-DatasetRoot`: override dataset folder manually.
- `-ResultRoot`: override result output folder manually.
- `-DefensePrompt`: override defense prompt file manually.
- `-GuardLevel`: default is `strict`.
- `-UseTaskMetadata`: default is `0`; keep this for fair visible-only defense.
- `-AppiumHost`: default is `127.0.0.1`.
- `-AppiumPort`: default is `4723`.
- `-AppiumBin`: override the Appium executable, for example `C:\Users\<you>\AppData\Roaming\npm\appium.cmd`.
- `-AppiumStartupTimeout`: default is `60` seconds.
- `-NoManageAppium`: do not start or stop Appium; use this only when Appium is already managed elsewhere.
- `-KeepAppium`: keep the Appium process alive if this launcher started it.
- Direct runner usage defaults to Appium management. Use `--no-manage-appium` on `attacks/quick_test_adb.py` or `attacks/quick_test_adb_fp.py` only when a wrapper already manages the service.

## Notes

- Do not hardcode real API keys into the script before sharing it.
- For fair evaluation, keep `-UseTaskMetadata 0`.
- If the other machine uses a different emulator port, set `-AdbPort`.
- The launcher writes results into a timestamped directory if `-ResultRoot` is not provided.
