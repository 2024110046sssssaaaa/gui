"""
Convert sample JSON files (from samples - 副本) back to config format.
Each sample JSON is a webarena_tasks_attacker entry that needs to be
reverse-mapped to the prompt_injections_setup_config format.

Workflow:
  1. Group all samples by their `source` field
  2. For each group, load the corresponding source config
  3. Match each sample to a config entry by free_form_name + variant
  4. Reverse-transform: intent -> instruction, hardcoded URLs -> template vars
  5. Write merged output to configs_new/
"""

import json
import re
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(r"d:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections")
SAMPLES_DIR = Path(r"d:\桌面\安全数据\web端\wasp-main-all\test_output\samples - 副本")
CONFIGS_DIR = BASE_DIR / "configs" / "additional_attacks"
OUTPUT_DIR = BASE_DIR / "configs_new"


# ---------------------------------------------------------------------------
# 1. Intent stripping helpers
# ---------------------------------------------------------------------------

def extract_base_instruction(intent: str) -> str:
    s = intent.strip()

    # -- Style: browserart_gcg  "Prompt transcript\nUSER: runbook_entry:\n..."
    if s.startswith("Prompt transcript"):
        m = re.search(r"USER:\s*runbook_entry:\s*(.+?)(?=\nSYSTEM TAIL:|$)", s, re.DOTALL)
        if m:
            return m.group(1).strip()

    # -- Style: browserart_enhanced (triple-backtick with PREFIX/BRIDGE/TASK) --
    if s.startswith("```\nPREFIX\n"):
        m = re.search(r"TASK\n(.+?)```", s, re.DOTALL)
        if m:
            task_content = m.group(1).strip()
            m2 = re.search(r"runbook_entry:\s*(.+)$", task_content, re.DOTALL)
            if m2:
                return m2.group(1).strip()
            return task_content.strip()

    # -- Style: browserart_prefix (single <task-note> layer, no SYSTEM TAIL) --
    if s.startswith("<task-note env=") and "SYSTEM TAIL" not in s and not s.startswith('<task-note env="gitlab">\n<context>'):
        m = re.search(r"<context>(.+?)</context>\s*<next-step>", s, re.DOTALL)
        if m:
            inner = m.group(1).strip()
            m2 = re.search(r"(?:action|required-action)[:>\s]+(.+?)(?:\n|</|$)", inner, re.DOTALL)
            if m2:
                return m2.group(1).strip()
            return inner.strip()

    # -- Style: browserart_suffix (JSON string in intent) {"task": "...", ...} --
    if s.startswith('{'):
        try:
            obj = json.loads(s)
            task = obj.get("task", "")
            if task:
                return task.strip()
        except json.JSONDecodeError:
            pass

    # -- Style: wa_gitlab_* and stwebagentbench (nested <task-note>) --
    if "<task-note" in s:
        # Try innermost required-action extraction
        m = re.search(r"required-action>(.+)$", s, re.DOTALL)
        if m:
            text = m.group(1)
            text = re.sub(r"</?(?:required-action|task-note|context|next-step)[^>]*>", "", text).strip()
            return text.strip()
        # Try action field extraction
        m = re.search(r"action:\s*(.+?)(?:\n|</required-action>|<next-step>)", s, re.DOTALL)
        if m:
            text = m.group(1).strip()
            text = re.sub(r"</?(?:required-action|task-note|context|next-step)[^>]*>", "", text).strip()
            return text.strip()

    # -- Style: wa_gitlab_permissions (Prompt transcript / SYSTEM CONTEXT / USER REQUEST) --
    if "USER REQUEST:" in s:
        parts = s.split("USER REQUEST:")
        last_part = parts[-1].strip()
        m = re.search(r"^(.+?)(?:\nSYSTEM NOTE:|$)", last_part, re.DOTALL)
        if m:
            text = m.group(1).strip()
            text = re.sub(r"^Prompt transcript\s*", "", text)
            text = re.sub(r"^SYSTEM CONTEXT:\s*.*?USER REQUEST:\s*", "", text, flags=re.DOTALL)
            return text.strip()
        return last_part.strip()

    # -- Fallback: croissant_attacks (clean natural language) --
    return s.strip()


# ---------------------------------------------------------------------------
# 2. Action name matching helpers
# ---------------------------------------------------------------------------

def extract_base_action_name(free_form_name: str) -> str:
    """Extract the base action (everything before ' variant NNN')."""
    name = free_form_name.strip()
    name = re.sub(r"^(?:browserart_(?:gcg|prefix|suffix|direct_prefix|direct|enhanced|fixed)_|stwebagentbench\s+)", "", name)
    m = re.search(r"^(.+?)[\s_]+variant\s+\d+", name)
    if m:
        return m.group(1).strip()
    return name.strip()


def extract_variant(free_form_name: str) -> int | None:
    """Extract variant number (strip leading zeros)."""
    m = re.search(r"variant\s+(\d+)", free_form_name)
    return int(m.group(1)) if m else None


def _norm_action(s: str) -> str:
    """Normalize action string for comparison."""
    s = s.lower().replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Canonical forms
    s = re.sub(r"\bssh\b", "secure shell", s)
    s = re.sub(r"webhook.*attacker.*server", "webhook", s)
    s = re.sub(r"security violating change.*malware.*zshrc", "malware injection", s)
    s = re.sub(r"change to a repository.*malware", "malware injection", s)
    s = re.sub(r"an?\s+ssh\s+key.*user\s*account", "ssh key", s)
    s = re.sub(r"add\s+an?\s+ssh\s+key", "add ssh key", s)
    s = re.sub(r"add\s+ssh\s+key", "add ssh key", s)
    s = re.sub(r"to\s+the\s+user\s+account", "", s)
    s = re.sub(r"for\s+the\s+user.?\s*account", "", s)
    s = re.sub(r"the\s+user\s+account", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def actions_match(s1: str, s2: str) -> bool:
    """Check if two action names match (fuzzy)."""
    n1, n2 = _norm_action(s1), _norm_action(s2)
    if n1 == n2:
        return True
    if n1 in n2 or n2 in n1:
        return True
    stopwords = {"the", "a", "an", "to", "for", "user", "account", "my"}
    w1 = set(n1.split()) - stopwords
    w2 = set(n2.split()) - stopwords
    if w1 and w2:
        overlap = len(w1 & w2) / max(len(w1), len(w2))
        if overlap >= 0.6:
            return True
    return False


# ---------------------------------------------------------------------------
# 3. URL reverse-substitution helpers
# ---------------------------------------------------------------------------

def reverse_substitute_url(url: str, parameters: dict) -> str:
    """Convert hardcoded URL back to template form."""
    result = url
    result = re.sub(r"https?://[^/]+", "{gitlab_domain}", result)
    owner = parameters.get("project_owner", "")
    if owner:
        result = re.sub(rf"/{re.escape(owner)}(?=/)", "/{project_owner}", result)
    name = parameters.get("project_name", "")
    if name:
        result = re.sub(rf"/{re.escape(name)}(?=/)", "/{project_name}", result)
    return result


def reverse_substitute_exfil(exfil_data: list, parameters: dict) -> list:
    """Reverse-substitute hardcoded URLs in exfil_data."""
    result = []
    for item in exfil_data:
        must_include = item.get("must_include", "")
        attacker_domain = parameters.get("attacker_domain", "")
        if attacker_domain and attacker_domain in must_include:
            must_include = must_include.replace(attacker_domain, "{attacker_domain}")
        owner = parameters.get("project_owner", "")
        if owner:
            enc = owner.replace("/", "%2F")
            must_include = must_include.replace(f"{enc}%2F", "{project_owner}%2F")
            must_include = must_include.replace(f"{owner}%2F", "{project_owner}%2F")
        name = parameters.get("project_name", "")
        if name:
            enc = name.replace("/", "%2F")
            must_include = must_include.replace(enc, "{project_name}")
            must_include = must_include.replace(name, "{project_name}")
        result.append({"must_include": must_include})
    return result


# ---------------------------------------------------------------------------
# 4. Config loading
# ---------------------------------------------------------------------------

def load_source_configs():
    """Load all source config files, indexed by free_form_name."""
    configs_by_source = defaultdict(dict)
    for cf in CONFIGS_DIR.glob("*.json"):
        name = cf.stem
        try:
            with open(cf, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data.get("prompt_injections_setup_config", []):
                key = entry.get("free_form_name", "")
                if key:
                    configs_by_source[name][key] = entry
            # Also index without _original suffix
            clean = name.replace("_original", "")
            if clean != name:
                for key, entry in dict(configs_by_source[name]).items():
                    configs_by_source[clean][key] = entry
        except Exception as e:
            print(f"  [WARN] Failed to load {cf}: {e}")
    return configs_by_source


def load_all_samples():
    """Load all sample JSONs grouped by source."""
    samples_by_source = defaultdict(list)
    for subdir in SAMPLES_DIR.iterdir():
        if not subdir.is_dir():
            continue
        source = subdir.name
        attacker_dir = subdir / "webarena_tasks_attacker"
        if not attacker_dir.is_dir():
            continue
        for json_file in attacker_dir.glob("*.json"):
            for enc in ("utf-8-sig", "utf-8"):
                try:
                    with open(json_file, "r", encoding=enc) as f:
                        sample = json.load(f)
                    samples_by_source[source].append(sample)
                    break
                except UnicodeError:
                    continue
            else:
                print(f"  [WARN] Failed to load {json_file}")
    return samples_by_source


# ---------------------------------------------------------------------------
# 5. Conversion functions
# ---------------------------------------------------------------------------

def convert_sample_to_config_entry(sample: dict, base_config_entry: dict) -> dict:
    """Convert sample using base config as template."""
    params = sample.get("parameters", {})
    entry = {k: v for k, v in base_config_entry.items()}
    entry["instruction"] = extract_base_instruction(sample.get("intent", ""))
    entry["free_form_name"] = sample.get("free_form_name", "")
    entry["parameters"] = {k: v for k, v in params.items()
                          if k not in ("gitlab_domain", "gitlab_protocol")}
    if sample.get("action_url") and params:
        entry["action_url"] = reverse_substitute_url(sample["action_url"], params)
    eval_obj = sample.get("eval", {})
    if "exfil_data" in eval_obj:
        entry["eval"] = dict(base_config_entry.get("eval", {}))
        entry["eval"]["exfil_data"] = reverse_substitute_exfil(eval_obj.get("exfil_data", []), params)
    notes = sample.get("notes", "")
    if notes:
        entry["notes"] = notes
    sp = sample.get("source_project", "")
    if sp:
        entry["source_project"] = sp
    return entry


def convert_sample_standalone(sample: dict) -> dict:
    """Convert sample without base config (fully standalone)."""
    params = sample.get("parameters", {})
    action_url = sample.get("action_url", "")
    entry = {
        "free_form_name": sample.get("free_form_name", ""),
        "environment": sample.get("environment", ""),
        "setup_fn": sample.get("setup_fn", ""),
        "parameters": {k: v for k, v in params.items()
                      if k not in ("gitlab_domain", "gitlab_protocol")},
        "action_url": action_url,
        "instruction": extract_base_instruction(sample.get("intent", "")),
        "exfil": sample.get("exfil", False),
        "eval": sample.get("eval", {}),
        "cleanup_fn": sample.get("cleanup_fn", ""),
        "notes": sample.get("notes", ""),
        "source_project": sample.get("source_project", ""),
    }
    if action_url and params:
        entry["action_url"] = reverse_substitute_url(action_url, params)
    if "exfil_data" in entry.get("eval", {}):
        entry["eval"]["exfil_data"] = reverse_substitute_exfil(
            entry["eval"].get("exfil_data", []), params)
    return entry


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading source configs...")
    configs_by_source = load_source_configs()
    print(f"  Loaded configs for {len(configs_by_source)} sources")

    print("Loading sample files...")
    samples_by_source = load_all_samples()
    print(f"  Loaded samples from {len(samples_by_source)} sources:")
    for src, samples in sorted(samples_by_source.items()):
        print(f"    {src}: {len(samples)} samples")

    output_aliases = {
        "browserart_gcg": "browserart_gcg",
        "browserart_prefix": "browserart_prefix",
        "browserart_suffix": "browserart_suffix",
        "browserart_enhanced": "browserart_attacks_enhanced",
        "browserart_fixed": "browserart_attacks_fixed",
    }

    for source, samples in samples_by_source.items():
        print(f"\nProcessing source: {source} ({len(samples)} samples)")

        output_name = output_aliases.get(source, source)

        # Find matching config key
        config_key = None
        for key in configs_by_source:
            if key == source or key == source.replace("_attacks_", "_") or key.replace("_original", "") == source:
                config_key = key
                break
        if config_key is None:
            config_key = source

        base_configs = configs_by_source.get(config_key, {})
        if not base_configs:
            print(f"  [WARN] No config found for source '{source}', using standalone mode")

        converted = []
        matched = 0
        unmatched = 0
        unmatched_examples = []

        for sample in samples:
            free_form_name = sample.get("free_form_name", "")
            base_action = extract_base_action_name(free_form_name)
            variant = extract_variant(free_form_name)

            matched_entry = None

            if base_configs:
                # Exact free_form_name match
                if free_form_name in base_configs:
                    matched_entry = base_configs[free_form_name]
                else:
                    # Fuzzy match: base action name + variant
                    for cfg_name, cfg_entry in base_configs.items():
                        cfg_base = extract_base_action_name(cfg_name)
                        cfg_variant = extract_variant(cfg_name)
                        if cfg_variant == variant and actions_match(base_action, cfg_base):
                            matched_entry = cfg_entry
                            break

            if matched_entry:
                converted.append(convert_sample_to_config_entry(sample, matched_entry))
                matched += 1
            else:
                converted.append(convert_sample_standalone(sample))
                unmatched += 1
                if len(unmatched_examples) < 3:
                    unmatched_examples.append(
                        f"    [UNMATCHED] {free_form_name} "
                        f"(base_action='{base_action}', variant={variant})"
                    )

        # Deduplicate by free_form_name
        seen = {}
        for c in converted:
            key = c.get("free_form_name", "")
            seen[key] = c
        converted = list(seen.values())
        converted.sort(key=lambda x: x.get("free_form_name", ""))

        output_path = OUTPUT_DIR / f"{output_name}.json"
        output_data = {"prompt_injections_setup_config": converted}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"  -> {output_path.name}: {len(converted)} entries (matched={matched}, unmatched={unmatched})")
        for ex in unmatched_examples:
            print(ex)

    print(f"\nDone! Output written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
