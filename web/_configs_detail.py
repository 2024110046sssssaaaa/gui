# -*- coding: utf-8 -*-
import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 分析 configs 目录中每个数据源在测试结果中的覆盖情况
results_file = r'D:\桌面\安全数据\web端\wasp-main-all\test_output\results_summary.json'
with open(results_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
results = data.get('results', [])

test_base_dir = r'D:\桌面\安全数据\web端\wasp-main-all\test_output\temp_tasks'

# 获取所有任务文件的 _is_attack 情况
all_tasks_info = {}
for fname in os.listdir(test_base_dir):
    if fname.endswith('.json'):
        tid = fname.replace('.json', '')
        fpath = os.path.join(test_base_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            tf = json.load(f)
        all_tasks_info[tid] = {
            'is_attack': tf.get('_is_attack', False),
            'environment': tf.get('environment', ''),
            'source': tf.get('source', ''),
        }

print('总任务配置文件数: %d' % len(all_tasks_info))

# 统计各 source 的任务数
from collections import Counter
src_all = Counter(v['source'] for v in all_tasks_info.values())
print('\n=== temp_tasks 中各 source 任务数 ===')
for k, v in src_all.most_common():
    print('  %-40s: %d' % (k, v))

# 统计各 source 在 results_summary 中的分布
print('\n=== results_summary 中各 source 任务数 ===')
src_results = Counter(r.get('source', '') for r in results)
for k, v in src_results.most_common():
    print('  %-40s: %d' % (k, v))

# 分析 merged_all 的详细来源
print('\n=== merged_all.json 详细分析 ===')
merged_all_file = r'D:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\experiment_config.merged_all.json'
with open(merged_all_file, 'r', encoding='utf-8') as f:
    merged = json.load(f)
attacks = merged.get('prompt_injections_setup_config', [])

# 统计 merged_all 中各子来源
merged_sub_src = Counter()
merged_env = Counter()
for a in attacks:
    # 看看是否有 source 字段
    src = a.get('source', a.get('prompt_injection', {}).get('source', 'unknown'))
    merged_sub_src[src] += 1
    merged_env[a.get('environment', 'unknown')] += 1

print('merged_all 总攻击数: %d' % len(attacks))
print('\nmerged_all 按 environment:')
for k, v in merged_env.most_common():
    print('  %s: %d' % (k, v))

# 查看 merged_all 中的前几个样本，看 source 是怎么来的
print('\nmerged_all 前3个样本:')
for a in attacks[:3]:
    keys = list(a.keys())
    print('  keys: %s' % keys)
    print('  environment: %s' % a.get('environment'))
    print('  free_form_name: %s' % a.get('free_form_name', '')[:60])
    pi = a.get('prompt_injection', {})
    print('  prompt_injection keys: %s' % list(pi.keys()) if pi else '  prompt_injection: (empty)')
    print()

# 看看 DATA_SOURCES 中每个数据源实际有多少任务
print('='*70)
print('DATA_SOURCES 中各数据源的原始数量 vs 实际测试数量')
print('='*70)

configs_dir = r'D:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\additional_attacks'

def count_file(path):
    if not os.path.exists(path):
        return 0, 'FILE_NOT_EXIST'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            if path.endswith('.jsonl'):
                return sum(1 for line in f if line.strip()), 'OK'
            data = json.load(f)
            if isinstance(data, list):
                return len(data), 'OK'
            elif isinstance(data, dict):
                arr = data.get('prompt_injections_setup_config', data.get('attacks', []))
                return len(arr), 'OK'
        return 0, 'UNKNOWN'
    except Exception as e:
        return 0, str(e)[:30]

sources = {
    'croissant_attacks': os.path.join(configs_dir, 'croissant', 'attacks_in_webarena_format.jsonl'),
    'croissant_utility': os.path.join(configs_dir, 'croissant', 'utility_in_webarena_format.jsonl'),
    'wa_gitlab_destructive': os.path.join(configs_dir, 'wa_gitlab_destructive.json'),
    'wa_gitlab_credential_exfil': os.path.join(configs_dir, 'wa_gitlab_credential_exfil.json'),
    'wa_gitlab_data_exfil': os.path.join(configs_dir, 'wa_gitlab_data_exfil.json'),
    'wa_gitlab_ssh_keys': os.path.join(configs_dir, 'wa_gitlab_ssh_keys.json'),
    'wa_gitlab_permissions': os.path.join(configs_dir, 'wa_gitlab_permissions.json'),
    'wa_reddit_harmful_content': os.path.join(configs_dir, 'wa_reddit_harmful_content.json'),
    'wa_reddit_destructive': os.path.join(configs_dir, 'wa_reddit_destructive.json'),
    'wa_reddit_data_exfil': os.path.join(configs_dir, 'wa_reddit_data_exfil.json'),
    'wa_reddit_account_hijack': os.path.join(configs_dir, 'wa_reddit_account_hijack.json'),
    'browserart_suffix': os.path.join(configs_dir, 'browserart_suffix.json'),
    'browserart_prefix': os.path.join(configs_dir, 'browserart_prefix.json'),
    'browserart_gcg': os.path.join(configs_dir, 'browserart_gcg.json'),
    'browserart_attacks_fixed': os.path.join(configs_dir, 'browserart_attacks_fixed.json'),
    'browserart_attacks_enhanced': os.path.join(configs_dir, 'browserart_attacks_enhanced.json'),
    'browserart_harmful_behaviors': os.path.join(configs_dir, 'browserart_harmful_behaviors.json'),
    'adinject_attacks': os.path.join(configs_dir, 'adinject_attacks.json'),
    'adinject_attacks_real_html': os.path.join(configs_dir, 'adinject_attacks_real_html.json'),
    'adinject_popup': os.path.join(configs_dir, 'adinject_popup.json'),
    'adinject_notification': os.path.join(configs_dir, 'adinject_notification.json'),
    'stwebagentbench': os.path.join(configs_dir, 'stwebagentbench_original.json'),
    'stwebagentbench_test': os.path.join(configs_dir, 'stwebagentbench', 'test.raw.json'),
    'merged_all': merged_all_file,
}

# 统计 results 中各 source 的数量
result_src_cnt = Counter(r.get('source', '') for r in results)

print('%-35s %10s %10s %10s' % ('data_source', '原始数量', '测试数量', '状态'))
print('-'*70)
for src, path in sorted(sources.items()):
    raw_cnt, status = count_file(path)
    tested_cnt = result_src_cnt.get(src, 0)
    if raw_cnt > 0 or tested_cnt > 0:
        print('%-35s %10s %10d %s' % (src, raw_cnt, tested_cnt, status))
    elif status != 'FILE_NOT_EXIST':
        print('%-35s %10s %10d %s' % (src, raw_cnt, tested_cnt, status))
