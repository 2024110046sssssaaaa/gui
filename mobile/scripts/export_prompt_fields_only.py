from __future__ import annotations

import ast
import fnmatch
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "project_prompt_fields_only.json"
OUTPUT_MD = ROOT / "project_prompt_fields_only.md"


INCLUDE_PATTERNS = [
    "mobile_safety/prompt/*.py",
    "mobile_safety/prompt/*.json",
    "attacks/llm_judge.py",
    "attacks/llm_judge_fp.py",
    "attacks/quick_test_adb.py",
    "attacks/quick_test_adb_fp.py",
    "mobile_safety/initialize/*.py",
]


NAME_KEYWORDS = {
    "prompt",
    "system_prompt",
    "instruction_prompt",
    "information_prompt",
    "additional_actions",
    "additional_action_description",
    "adversarial_prompt",
    "advserairl_prompt",
}


JSON_PROMPT_KEYS = {
    "name",
    "purpose",
    "mobile_defense_system_append",
    "json_action_agent_append",
    "strict_action_agent_append",
    "sandwich_pre_observation",
    "sandwich_post_observation",
    "integration_note",
}


def should_include(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(fnmatch.fnmatch(rel, pattern) for pattern in INCLUDE_PATTERNS)


def target_names(target: ast.expr) -> list[str]:
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in target.elts:
            names.extend(target_names(elt))
        return names
    return []


def name_is_prompt_like(name: str) -> bool:
    lowered = name.lower()
    return any(key in lowered for key in NAME_KEYWORDS)


def literal_value(node: ast.AST):
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def normalize_value(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if isinstance(item, (str, int, float, bool)) or item is None:
                normalized[key] = item
            elif isinstance(item, (list, tuple)):
                kept = [x for x in item if isinstance(x, (str, int, float, bool)) or x is None]
                if kept:
                    normalized[key] = kept
        return normalized if normalized else None
    if isinstance(value, (list, tuple)):
        kept = [x for x in value if isinstance(x, (str, int, float, bool)) or x is None]
        return kept if kept else None
    return None


def extract_from_python(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(text)
    results: list[dict] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.scope: list[str] = []

        def add_result(self, field_name: str, value, lineno: int):
            normalized = normalize_value(value)
            if normalized in (None, "", [], {}):
                return
            results.append(
                {
                    "source_file": path.relative_to(ROOT).as_posix(),
                    "field_name": ".".join(self.scope + [field_name]) if self.scope else field_name,
                    "line": lineno,
                    "prompt_value": normalized,
                }
            )

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_Assign(self, node: ast.Assign):
            names: list[str] = []
            for target in node.targets:
                names.extend(target_names(target))
            for name in names:
                if name_is_prompt_like(name):
                    self.add_result(name, literal_value(node.value), node.lineno)
            self.generic_visit(node)

        def visit_AnnAssign(self, node: ast.AnnAssign):
            names = target_names(node.target)
            for name in names:
                if name_is_prompt_like(name):
                    self.add_result(name, literal_value(node.value), node.lineno)
            self.generic_visit(node)

    Visitor().visit(tree)
    return results


def extract_from_json(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    results: list[dict] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key in JSON_PROMPT_KEYS:
                normalized = normalize_value(value)
                if normalized not in (None, "", [], {}):
                    results.append(
                        {
                            "source_file": path.relative_to(ROOT).as_posix(),
                            "field_name": key,
                            "line": None,
                            "prompt_value": normalized,
                        }
                    )
    return results


def collect() -> list[dict]:
    records: list[dict] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not should_include(path):
            continue
        if path.suffix.lower() == ".py":
            records.extend(extract_from_python(path))
        elif path.suffix.lower() == ".json":
            records.extend(extract_from_json(path))
    return records


def write_outputs(records: list[dict]) -> None:
    OUTPUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Project Prompt Fields Only")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append(f"Total prompt fields: {len(records)}")
    lines.append("")
    for record in records:
        lines.append(f"## `{record['source_file']}` :: `{record['field_name']}`")
        if record["line"] is not None:
            lines.append("")
            lines.append(f"Line: `{record['line']}`")
        lines.append("")
        value = record["prompt_value"]
        if isinstance(value, str):
            lines.append("```text")
            lines.append(value.rstrip())
            lines.append("```")
        else:
            lines.append("```json")
            lines.append(json.dumps(value, ensure_ascii=False, indent=2))
            lines.append("```")
        lines.append("")
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    records = collect()
    write_outputs(records)
    print(str(OUTPUT_JSON))
    print(str(OUTPUT_MD))


if __name__ == "__main__":
    main()
