# GitHub Upload Checklist

Use this checklist before pushing the repository to GitHub.

## Current Recommendation

Do not upload the raw working directory without `.gitignore`.

This local copy contains:

- Runtime logs and screenshots.
- Many timestamped result folders.
- Local Android/Appium state folders.
- One-off debug/demo/test scripts.
- Large APK files.
- Previously hardcoded API-key shaped strings that have been replaced with placeholders.

## Files That Should Be Tracked

Core project:

- `README.md`
- `LICENSE.txt`
- `requirements.txt`
- `setup.py`
- `.gitignore`
- `.env.example`
- `attacks/`
- `mobile_safety/`
- `asset/`
- `experiment/`
- `docs/`
- `scripts/run_mobile_guard_portable.ps1`
- `scripts/export_project_prompts.py`
- `scripts/export_prompt_fields_only.py`

Current local additions worth keeping:

- `docs/project_inventory.md`
- `docs/dataset_inventory.csv`
- `docs/mobile_guard_portable_usage.md`

## Files That Should Not Be Tracked

Generated outputs:

- `logs/`
- `result*/`
- `qwen*/`
- `qianwen*/`
- `*_result/`
- `result_summary/`

Local state:

- `.android-home/`
- `.android_home/`
- `.appium/`
- `.idea/`
- `.vscode/`
- `__pycache__/`

Large binaries:

- `*.apk`
- `*.idsig`

If APKs are required for public reproduction, use Git LFS or publish them as
release assets with checksums. `Joplin.apk` is close to GitHub's hard file-size
limit and should not be committed normally.

One-off local scripts/artifacts:

- root-level `debug_*.py`
- root-level `demo_*.py`
- root-level `test_*.py`
- root-level screenshots and XML dumps
- `appendix_*.json`
- `project_prompts_dump.md`
- `project_prompt_fields_only.*`

## Secret Check

Before committing, run:

```powershell
Select-String -Path (Get-ChildItem -Recurse -File | Where-Object {
  $_.FullName -notmatch '\\.git\\|\\logs\\|\\result_|\\qwen_|\\qianwen_|__pycache__'
}).FullName -Pattern 'sk-[A-Za-z0-9_-]{20,}|sk-or-[A-Za-z0-9_-]{20,}' -AllMatches
```

Expected result: no real API keys. Placeholders such as
`REPLACE_WITH_API_KEY` are acceptable.

Also verify no private SSH passwords or server IP credentials are committed.

## Suggested First Commit

```powershell
git init
git status --ignored
git add README.md LICENSE.txt requirements.txt setup.py .gitignore .env.example
git add attacks mobile_safety asset experiment docs
git add scripts\run_mobile_guard_portable.ps1 scripts\export_project_prompts.py scripts\export_prompt_fields_only.py
git status
git commit -m "Prepare MobileSafetyBench for public release"
```

Inspect `git status` carefully before committing.

## If You Need APKs

Option A: Git LFS

```powershell
git lfs install
git lfs track "*.apk"
git add .gitattributes
git add asset\environments\resource\apks\*.apk
```

Option B: Release assets

- Upload APKs to a GitHub Release.
- Add SHA256 checksums.
- Document download paths in README.
