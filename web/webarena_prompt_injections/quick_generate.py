"""快速生成测试样本的脚本"""
import os
import json
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

configs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")

DATA_SOURCES = {
    # WebArena GitLab 攻击数据
    "wa_gitlab_destructive": os.path.join(configs_dir, "additional_attacks", "wa_gitlab_destructive.json"),
    "wa_gitlab_credential_exfil": os.path.join(configs_dir, "additional_attacks", "wa_gitlab_credential_exfil.json"),
    "wa_gitlab_data_exfil": os.path.join(configs_dir, "additional_attacks", "wa_gitlab_data_exfil.json"),
    "wa_gitlab_ssh_keys": os.path.join(configs_dir, "additional_attacks", "wa_gitlab_ssh_keys.json"),
    "wa_gitlab_permissions": os.path.join(configs_dir, "additional_attacks", "wa_gitlab_permissions.json"),
    # BrowserArt 攻击数据 (GitLab)
    "browserart_suffix": os.path.join(configs_dir, "additional_attacks", "browserart_suffix.json"),
    "browserart_prefix": os.path.join(configs_dir, "additional_attacks", "browserart_prefix.json"),
    "browserart_gcg": os.path.join(configs_dir, "additional_attacks", "browserart_gcg.json"),
    "browserart_attacks_fixed": os.path.join(configs_dir, "additional_attacks", "browserart_attacks_fixed.json"),
    "browserart_attacks_enhanced": os.path.join(configs_dir, "additional_attacks", "browserart_attacks_enhanced.json"),
    # Croissant 基准数据 (GitLab)
    "croissant_attacks": os.path.join(configs_dir, "croissant", "attacks_in_webarena_format.jsonl"),
    # STWebAgentBench (GitLab)
    "stwebagentbench": os.path.join(configs_dir, "additional_attacks", "stwebagentbench_original.json"),
}

def load_jsonl(filepath):
    items = []
    if not os.path.exists(filepath): return items
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: items.append(json.loads(line))
            except: pass
    return items

def load_json(filepath):
    if not os.path.exists(filepath): return []
    try:
        data = json.load(open(filepath, 'r', encoding='utf-8'))
        if isinstance(data, dict) and "prompt_injections_setup_config" in data:
            return data["prompt_injections_setup_config"]
        elif isinstance(data, list): return data
        return []
    except: return []

def extract_environment(item):
    if "environment" in item: return item["environment"]
    if "sites" in item:
        sites = item.get("sites", [])
        if isinstance(sites, list) and sites: return sites[0]
    return "unknown"

def is_attack_task(item):
    if item.get("exfil", False): return True
    instruction = item.get("instruction", "").lower()
    attack_keywords = ["attacker", "exfil", "steal", "malicious", "delete my project"]
    return any(kw in instruction for kw in attack_keywords)

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = os.path.join(r'd:/桌面/安全数据/web端/wasp-main-all', 'test_output', f'gitlab_tests_{timestamp}')
    samples_dir = os.path.join(output_base, "samples", timestamp)
    os.makedirs(samples_dir, exist_ok=True)

    total_items = 0
    total_benign = 0
    total_attack = 0

    for source_name, source_path in DATA_SOURCES.items():
        if source_path.endswith('.jsonl'):
            items = load_jsonl(source_path)
        else:
            items = load_json(source_path)

        if not items: continue

        # 只取 gitlab 环境
        gitlab_items = [x for x in items if isinstance(x, dict) and extract_environment(x) == "gitlab"]
        if not gitlab_items: continue

        sample_dir = os.path.join(samples_dir, source_name)
        webarena_tasks_dir = os.path.join(sample_dir, "webarena_tasks")
        webarena_tasks_attacker_dir = os.path.join(sample_dir, "webarena_tasks_attacker")
        os.makedirs(webarena_tasks_dir, exist_ok=True)
        os.makedirs(webarena_tasks_attacker_dir, exist_ok=True)

        benign_count = 0
        attack_count = 0
        task_id = 3000

        for item in gitlab_items:
            is_attack = is_attack_task(item)

            if is_attack:
                attack_count += 1
                out_path = os.path.join(webarena_tasks_attacker_dir, f"{task_id}.json")
            else:
                benign_count += 1
                out_path = os.path.join(webarena_tasks_dir, f"{task_id}.json")

            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(item, f, ensure_ascii=False, indent=2)

            task_id += 1

        print(f"{source_name}: {len(gitlab_items)} gitlab, {benign_count} benign, {attack_count} attack")
        total_items += len(gitlab_items)
        total_benign += benign_count
        total_attack += attack_count

    print(f"\n总计: {total_items} 条任务, {total_benign} benign, {total_attack} attack")
    print(f"样本目录: {samples_dir}")
    return samples_dir

if __name__ == "__main__":
    main()
