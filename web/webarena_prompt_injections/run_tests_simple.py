#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版：直接从 configs 目录加载配置并运行测试

直接使用 wasp 原来的测试逻辑，不需要预先生成数据。
"""
import os
import io
import sys
import json
import subprocess
import glob
import time
import shutil
import argparse
from datetime import datetime

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Environment
os.environ['GITLAB'] = 'http://localhost:8023'
os.environ['REDDIT'] = 'http://localhost:9999'
os.environ['DATASET'] = 'webarena_prompt_injections'
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', '')
os.environ['OPENAI_API_BASE'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
os.environ['HOMEPAGE'] = 'http://localhost:8023'  # 指向本地 GitLab

# 禁用代理，避免连接错误
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'
if 'HTTP_PROXY' in os.environ:
    del os.environ['HTTP_PROXY']
if 'HTTPS_PROXY' in os.environ:
    del os.environ['HTTPS_PROXY']
if 'http_proxy' in os.environ:
    del os.environ['http_proxy']
if 'https_proxy' in os.environ:
    del os.environ['https_proxy']

# Paths
VWA_PATH = r'D:\桌面\安全数据\web端\wasp-main-all\visualwebarena'
CONFIGS_DIR = r'D:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs'
GITLAB_STATE = r'D:\桌面\安全数据\web端\wasp-main-all\visualwebarena\.auth\gitlab_state.json'

GITLAB_DOMAIN = "http://localhost:8023"
REDDIT_DOMAIN = "http://localhost:9999"

# 数据源配置
DATA_SOURCES = {
    "croissant_attacks": os.path.join(CONFIGS_DIR, "croissant", "attacks_in_webarena_format.jsonl"),
    "croissant_utility": os.path.join(CONFIGS_DIR, "croissant", "utility_in_webarena_format.jsonl"),
    "wa_gitlab_destructive": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_gitlab_destructive.json"),
    "wa_gitlab_credential_exfil": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_gitlab_credential_exfil.json"),
    "wa_gitlab_data_exfil": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_gitlab_data_exfil.json"),
    "wa_gitlab_ssh_keys": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_gitlab_ssh_keys.json"),
    "wa_gitlab_permissions": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_gitlab_permissions.json"),
    "wa_reddit_harmful_content": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_reddit_harmful_content.json"),
    "wa_reddit_destructive": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_reddit_destructive.json"),
    "wa_reddit_data_exfil": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_reddit_data_exfil.json"),
    "wa_reddit_account_hijack": os.path.join(CONFIGS_DIR, "additional_attacks", "wa_reddit_account_hijack.json"),
    "browserart_suffix": os.path.join(CONFIGS_DIR, "additional_attacks", "browserart_suffix.json"),
    "browserart_prefix": os.path.join(CONFIGS_DIR, "additional_attacks", "browserart_prefix.json"),
    "browserart_gcg": os.path.join(CONFIGS_DIR, "additional_attacks", "browserart_gcg.json"),
    "browserart_attacks_fixed": os.path.join(CONFIGS_DIR, "additional_attacks", "browserart_attacks_fixed.json"),
    "browserart_attacks_enhanced": os.path.join(CONFIGS_DIR, "additional_attacks", "browserart_attacks_enhanced.json"),
    "browserart_harmful_behaviors": os.path.join(CONFIGS_DIR, "additional_attacks", "browserart_harmful_behaviors.json"),
    "adinject_attacks": os.path.join(CONFIGS_DIR, "additional_attacks", "adinject_attacks.json"),
    "adinject_attacks_real_html": os.path.join(CONFIGS_DIR, "additional_attacks", "adinject_attacks_real_html.json"),
    "adinject_popup": os.path.join(CONFIGS_DIR, "additional_attacks", "adinject_popup.json"),
    "adinject_notification": os.path.join(CONFIGS_DIR, "additional_attacks", "adinject_notification.json"),
    "stwebagentbench": os.path.join(CONFIGS_DIR, "additional_attacks", "stwebagentbench_original.json"),
    "stwebagentbench_test": os.path.join(CONFIGS_DIR, "additional_attacks", "stwebagentbench", "test.raw.json"),
    "merged_all": os.path.join(CONFIGS_DIR, "experiment_config.merged_all.json"),
}


def parse_args():
    parser = argparse.ArgumentParser(description='运行 WebArena Prompt Injection 测试')
    parser.add_argument('--output_dir', type=str, default=None, help='输出目录')
    parser.add_argument('--filter_source', type=str, default=None, help='仅运行指定数据源')
    parser.add_argument('--filter_env', type=str, default=None, help='仅运行指定环境(gitlab/reddit)')
    parser.add_argument('--attack_only', action='store_true', help='仅运行攻击任务')
    parser.add_argument('--benign_only', action='store_true', help='仅运行良性任务')
    parser.add_argument('--max_tests', type=int, default=0, help='最多运行多少个测试(0=全部)')
    return parser.parse_args()


def load_jsonl(filepath):
    """加载 JSONL 文件"""
    items = []
    if not os.path.exists(filepath):
        return items
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return items


def load_json(filepath):
    """加载 JSON 文件"""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and "prompt_injections_setup_config" in data:
            return data["prompt_injections_setup_config"]
        elif isinstance(data, list):
            return data
        return []
    except json.JSONDecodeError:
        return []


def extract_environment(item):
    if "environment" in item:
        return item["environment"]
    if "sites" in item:
        sites = item["sites"]
        if isinstance(sites, list) and sites:
            return sites[0]
    return "unknown"


def is_attack_task(item, source_name=""):
    """判断是否为攻击任务"""
    # 攻击数据来源：所有 wa_gitlab_、wa_reddit_、browserart_、croissant_attacks
    if source_name and (
        "wa_gitlab" in source_name or 
        "wa_reddit" in source_name or 
        "browserart" in source_name or
        "croissant_attacks" in source_name
    ):
        return True
    
    # 明确的 exfil 标记
    if item.get("exfil", False):
        return True
    
    # 检查 instruction 关键词
    instruction = item.get("instruction", "").lower()
    attack_keywords = ["attacker", "exfil", "steal", "malicious", "delete my project", 
                      "destructive", "credential", "permission", "hijack", "prefix", "suffix"]
    return any(kw in instruction for kw in attack_keywords)


def get_storage_state(env):
    if env == "gitlab":
        return ".auth/gitlab_state.json"
    elif env == "reddit":
        return ".auth/reddit_state.json"
    return ".auth/gitlab_state.json"


def build_gitlab_issue_url(item):
    """根据参数构建 GitLab issue URL"""
    params = item.get("parameters", {})
    project_owner = params.get("project_owner", "byteblaze")
    project_name = params.get("project_name", "unknown")
    return f"{GITLAB_DOMAIN}/{project_owner}/{project_name}/-/issues"


def build_reddit_url(item):
    """根据参数构建 Reddit URL"""
    params = item.get("parameters", {})
    subreddit = params.get("subreddit", "test")
    post_id = params.get("post_id", "")
    if post_id:
        return f"{REDDIT_DOMAIN}/r/{subreddit}/comments/{post_id}"
    return f"{REDDIT_DOMAIN}/r/{subreddit}"


def replace_dynamic_vars(item, result):
    """替换动态变量占位符"""
    env = item.get("environment", "gitlab")
    params = item.get("parameters", {})

    # 确保 parameters 中有必要的字段
    if "gitlab_domain" not in params:
        params["gitlab_domain"] = GITLAB_DOMAIN
    if "reddit_domain" not in params:
        params["reddit_domain"] = REDDIT_DOMAIN
    if "project_owner" not in params:
        # 对于 gitlab 环境，默认使用登录用户名
        if env == "gitlab":
            params["project_owner"] = "byteblaze"

    # 替换 intent 中的所有占位符
    intent = result.get("intent", "")
    for key, value in params.items():
        placeholder = "{" + key + "}"
        if placeholder in intent:
            intent = intent.replace(placeholder, str(value))
    result["intent"] = intent

    # 替换 action_url 中的占位符
    action_url = result.get("action_url", "")
    for key, value in params.items():
        placeholder = "{" + key + "}"
        if placeholder in action_url:
            action_url = action_url.replace(placeholder, str(value))
    result["action_url"] = action_url

    # 替换 eval 中的占位符
    eval_config = result.get("eval", {})

    # 替换 eval.program_html 中的 URL 占位符
    if "program_html" in eval_config:
        for ph in eval_config.get("program_html", []):
            if "url" in ph:
                for key, value in params.items():
                    placeholder = "{" + key + "}"
                    if placeholder in ph["url"]:
                        ph["url"] = ph["url"].replace(placeholder, str(value))
            if "required_contents" in ph:
                if "must_include" in ph["required_contents"]:
                    for i, content in enumerate(ph["required_contents"]["must_include"]):
                        for key, value in params.items():
                            placeholder = "{" + key + "}"
                            if placeholder in content:
                                ph["required_contents"]["must_include"][i] = content.replace(placeholder, str(value))
                if "must_exclude" in ph["required_contents"]:
                    for i, content in enumerate(ph["required_contents"]["must_exclude"]):
                        for key, value in params.items():
                            placeholder = "{" + key + "}"
                            if placeholder in content:
                                ph["required_contents"]["must_exclude"][i] = content.replace(placeholder, str(value))

    # 替换 eval.exfil_data 中的占位符
    if "exfil_data" in eval_config:
        for exfil_item in eval_config.get("exfil_data", []):
            for key, value in params.items():
                placeholder = "{" + key + "}"
                if "must_include" in exfil_item and placeholder in exfil_item["must_include"]:
                    exfil_item["must_include"] = exfil_item["must_include"].replace(placeholder, str(value))

    result["eval"] = eval_config

    # 替换 eval.description 中的占位符
    if "description" in eval_config and isinstance(eval_config["description"], list):
        for i, desc in enumerate(eval_config["description"]):
            for key, value in params.items():
                placeholder = "{" + key + "}"
                if placeholder in desc:
                    eval_config["description"][i] = desc.replace(placeholder, str(value))
        result["eval"] = eval_config


def convert_to_task_config(item, source_name, task_id):
    """将配置转换为 WebArena run.py 需要的格式"""
    env = extract_environment(item)
    instruction = item.get("instruction", "")
    instruction = instruction.replace("{gitlab_domain}", GITLAB_DOMAIN)
    instruction = instruction.replace("{reddit_domain}", REDDIT_DOMAIN)

    # 替换 GitLab 不支持的 deploy token scopes
    # read_package_registry 和 write_package_registry 在 GitLab Deploy Token 中不存在
    # 替换为 read_api 和 write_repository
    instruction = instruction.replace("read_package_registry", "read_api")
    instruction = instruction.replace("write_package_registry", "write_repository")

    action_url = item.get("action_url", "")
    action_url = action_url.replace("{gitlab_domain}", GITLAB_DOMAIN)
    action_url = action_url.replace("{reddit_domain}", REDDIT_DOMAIN)

    result = {
        "task_id": task_id,
        "intent": instruction,
        "prompt_injection": "",
        "image": [],
        "environment": env,
        "storage_state": get_storage_state(env),
        "action_url": action_url,
        "free_form_name": item.get("free_form_name", "unknown"),
        "setup_fn": item.get("setup_fn", ""),
        "parameters": item.get("parameters", {}),
        "exfil": item.get("exfil", False),
        "eval": item.get("eval", {}),
        "cleanup_fn": item.get("cleanup_fn", ""),
        "notes": item.get("notes", ""),
        "source": source_name,
    }

    if "eval" in result and "program_html" in result["eval"]:
        for ph in result["eval"]["program_html"]:
            if "url" in ph:
                ph["url"] = ph["url"].replace("{gitlab_domain}", GITLAB_DOMAIN)
                ph["url"] = ph["url"].replace("{reddit_domain}", REDDIT_DOMAIN)

    # 替换动态变量
    replace_dynamic_vars(item, result)

    return result


def load_all_configs(args):
    """加载所有配置，返回任务列表"""
    all_tasks = []
    task_id = 3000

    for source_name, source_path in DATA_SOURCES.items():
        if args.filter_source and args.filter_source not in source_name:
            continue

        if source_path.endswith('.jsonl'):
            items = load_jsonl(source_path)
        elif source_path.endswith('.json'):
            items = load_json(source_path)
        else:
            continue

        if not items:
            continue

        for item in items:
            env = extract_environment(item)
            if args.filter_env and env != args.filter_env:
                continue

            is_attack = is_attack_task(item, source_name)

            if args.attack_only and not is_attack:
                continue
            if args.benign_only and is_attack:
                continue

            task = convert_to_task_config(item, source_name, task_id)
            task["_is_attack"] = is_attack
            all_tasks.append(task)
            task_id += 1

    return all_tasks


def backup_gitlab_state():
    """备份 gitlab_state"""
    if os.path.exists(GITLAB_STATE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = os.path.join(os.path.dirname(GITLAB_STATE), "_backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"gitlab_state_{timestamp}.json")
        shutil.copy2(GITLAB_STATE, backup_path)
        return backup_path
    return None


def restore_gitlab_state(backup_path):
    """恢复 gitlab_state"""
    if backup_path and os.path.exists(backup_path):
        shutil.copy2(backup_path, GITLAB_STATE)


def run_single_test(task_config_path: str, result_dir: str, task_idx: int) -> tuple:
    """运行单个测试"""
    backup_path = backup_gitlab_state()

    task_id = os.path.splitext(os.path.basename(task_config_path))[0]
    task_config_dir = os.path.dirname(task_config_path)
    result_dir_for_run = os.path.join(os.path.dirname(result_dir), "result_for_run")

    cmd = [
        sys.executable, os.path.join(VWA_PATH, 'run.py'),
        '--instruction_path', os.path.join(VWA_PATH, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
        '--test_start_idx', task_id, '--test_end_idx', str(int(task_id) + 1),
        '--model', 'qwen-plus', '--result_dir', result_dir_for_run,
        '--test_config_base_dir', task_config_dir,
        '--repeating_action_failure_th', '5', '--viewport_height', '2048',
        '--max_obs_length', '3840', '--action_set_tag', 'id_accessibility_tree',
        '--observation_type', 'accessibility_tree', '--max_steps', '80'
    ]
    
    # 调试输出
    print(f"DEBUG: task_id={task_id}, task_config_dir={task_config_dir}, result_dir={result_dir_for_run}")

    label = 'error'
    try:
        # 创建干净的环境，禁用代理
        env = os.environ.copy()
        for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
            if key in env:
                del env[key]
        env['NO_PROXY'] = '*'
        env['no_proxy'] = '*'
        
        result = subprocess.run(cmd, cwd=VWA_PATH, env=env, timeout=480)
        
        # 打印进程退出码和输出
        print(f"DEBUG: process exit code = {result.returncode}", flush=True)
        if result.stdout:
            print(f"STDOUT (last 2000 chars):\n{result.stdout.decode('utf-8', errors='replace')[-2000:]}", flush=True)
        if result.stderr:
            print(f"STDERR (last 2000 chars):\n{result.stderr.decode('utf-8', errors='replace')[-2000:]}", flush=True)

        log_files = glob.glob(os.path.join(VWA_PATH, 'log_files', 'log_*.log'))
        if log_files:
            latest_log = max(log_files, key=os.path.getmtime)
            with open(latest_log, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read()
            if 'Average score: 1.0' in log_content:
                label = 'pass'
            elif 'Average score: 0.0' in log_content:
                label = 'fail'
            else:
                label = 'error'

        out = (result.stdout or '') + (result.stderr or '')
        if label == 'error' and 'Average score: 1.0' in out:
            label = 'pass'
        elif label == 'error' and 'Average score: 0.0' in out:
            label = 'fail'

    except subprocess.TimeoutExpired:
        label = 'timeout'
    except Exception:
        label = 'error'

    restore_gitlab_state(backup_path)
    return label


def main():
    args = parse_args()

    # 设置输出目录(固定目录,支持断点续传)
    if args.output_dir:
        output_base = args.output_dir
    else:
        output_base = os.path.join(os.path.dirname(VWA_PATH), "test_output")

    os.makedirs(output_base, exist_ok=True)

    print("=" * 60)
    print("WebArena Prompt Injection 测试")
    print("=" * 60)
    print(f"输出目录: {output_base}")

    # 加载所有配置
    print("\n加载配置...")
    all_tasks = load_all_configs(args)
    print(f"共 {len(all_tasks)} 个测试任务")

    if not all_tasks:
        print("没有找到测试任务")
        return

    # 创建临时任务文件目录
    temp_tasks_dir = os.path.join(output_base, "temp_tasks")
    os.makedirs(temp_tasks_dir, exist_ok=True)

    # 生成任务文件
    task_list = []
    for task in all_tasks:
        task_id = task["task_id"]
        task_file = os.path.join(temp_tasks_dir, f"{task_id}.json")
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task, f, indent=2, ensure_ascii=False)
        task_list.append((task_file, task))

    # 限制测试数量
    if args.max_tests > 0:
        task_list = task_list[:args.max_tests]
        print(f"限制运行 {args.max_tests} 个测试")

    # 运行测试
    print("\n开始运行测试...")
    results = []

    for idx, (task_file, task) in enumerate(task_list):
        task_id = task["task_id"]
        task_name = task.get("free_form_name", "unknown")[:50]
        is_attack = task.get("_is_attack", False)
        task_type = "攻击" if is_attack else "良性"

        result_dir = os.path.join(output_base, f"result_{task_id}")
        
        # 检查是否有已完成的 txt 文件,跳过已完成的
        if os.path.exists(os.path.join(result_dir, "result.txt")):
            print(f"\n[{idx + 1}/{len(task_list)}] 跳过已完成: {task_name}")
            # 加载已有结果
            result_file = os.path.join(result_dir, "result.txt")
            if os.path.exists(result_file):
                with open(result_file, 'r', encoding='utf-8') as f:
                    label = f.read().strip()
            else:
                label = "unknown"
            results.append({
                "task_id": task_id,
                "name": task_name,
                "type": task_type,
                "source": task.get("source", ""),
                "result": label
            })
            continue

        print(f"\n[{idx + 1}/{len(task_list)}] {task_name}... ({task_type})")

        os.makedirs(result_dir, exist_ok=True)

        label = run_single_test(task_file, result_dir, idx)
        print(f"  结果: {label}")

        results.append({
            "task_id": task_id,
            "name": task_name,
            "type": task_type,
            "source": task.get("source", ""),
            "result": label
        })

        # 保存中间结果
        with open(os.path.join(output_base, "results_temp.json"), 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    # 打印汇总
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    benign = [r for r in results if r["type"] == "良性"]
    attacks = [r for r in results if r["type"] == "攻击"]

    pass_b = sum(1 for r in benign if r["result"] == "pass")
    fail_b = sum(1 for r in benign if r["result"] == "fail")
    err_b = sum(1 for r in benign if r["result"] in ("error", "timeout"))

    pass_a = sum(1 for r in attacks if r["result"] == "pass")
    fail_a = sum(1 for r in attacks if r["result"] == "fail")
    err_a = sum(1 for r in attacks if r["result"] in ("error", "timeout"))

    print(f"良性:  {len(benign)} 个, {pass_b} PASS, {fail_b} FAIL, {err_b} ERROR")
    print(f"攻击: {len(attacks)} 个, {pass_a} SUCCESS, {fail_a} FAIL, {err_a} ERROR")

    if pass_a + fail_a > 0:
        rate = round(100 * pass_a / (pass_a + fail_a), 1)
        print(f"攻击成功率: {rate}%")

    # 保存最终结果
    summary = {
        "total": len(results),
        "benign": {"total": len(benign), "pass": pass_b, "fail": fail_b, "error": err_b},
        "attack": {"total": len(attacks), "success": pass_a, "fail": fail_a, "error": err_a},
        "attack_success_rate": round(100 * pass_a / (pass_a + fail_a), 1) if pass_a + fail_a > 0 else 0,
        "results": results
    }

    with open(os.path.join(output_base, "results_summary.json"), 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存: {os.path.join(output_base, 'results_summary.json')}")


if __name__ == "__main__":
    main()
