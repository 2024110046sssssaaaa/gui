from __future__ import annotations

import fnmatch
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "project_prompts_dump.md"


INCLUDE_PATTERNS = [
    "mobile_safety/prompt/*.py",
    "mobile_safety/prompt/*.json",
    "attacks/llm_judge.py",
    "attacks/llm_judge_fp.py",
    "attacks/quick_test_adb.py",
    "attacks/quick_test_adb_fp.py",
    "attacks/_attack_runner.py",
    "attacks/quick_test_runner.py",
    "mobile_safety/initialize/*.py",
]


PROMPT_MARKERS = [
    "SYSTEM_PROMPT",
    "INSTRUCTION_PROMPT",
    "INFORMATION_PROMPT",
    "SYS_PROMPT",
    "system_prompt =",
    "mobile_defense_system_append",
    "sandwich_pre_observation",
    "sandwich_post_observation",
    "adversarial_prompt",
    "advserairl_prompt",
    "get_task_specific_prompt",
]


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(fnmatch.fnmatch(rel, pattern) for pattern in INCLUDE_PATTERNS)


def looks_prompt_related(path: Path) -> bool:
    if path.suffix.lower() not in {".py", ".json", ".md"}:
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    return any(marker in text for marker in PROMPT_MARKERS)


def iter_prompt_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if not should_include(path):
            continue
        if not looks_prompt_related(path):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def fence_lang(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix == ".json":
        return "json"
    if suffix == ".md":
        return "markdown"
    return ""


def main() -> None:
    files = iter_prompt_files()
    lines: list[str] = []
    lines.append("# Project Prompts Dump")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("This file collects prompt-related source files from the project, including:")
    lines.append("")
    lines.append("- Agent base prompts and task-specific prompts under `mobile_safety/prompt/`")
    lines.append("- Attack judge prompt in `attacks/llm_judge.py`")
    lines.append("- False-positive judge prompt in `attacks/llm_judge_fp.py`")
    lines.append("- ADB runner prompts in `attacks/quick_test_adb.py` and `attacks/quick_test_adb_fp.py`")
    lines.append("- Prompt-injection / adversarial initialization snippets under `mobile_safety/initialize/`")
    lines.append("")
    lines.append(f"Total files: {len(files)}")
    lines.append("")
    lines.append("## File List")
    lines.append("")
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        lines.append(f"- `{rel}`")
    lines.append("")

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="replace")
        lines.append(f"## `{rel}`")
        lines.append("")
        lines.append(f"```{fence_lang(path)}")
        lines.append(content.rstrip())
        lines.append("```")
        lines.append("")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(str(OUTPUT))


if __name__ == "__main__":
    main()
