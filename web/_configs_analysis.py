# -*- coding: utf-8 -*-
import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 1. 统计 merged_all.json 中的所有 prompt_injections_setup_config
merged_all_file = r'D:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\experiment_config.merged_all.json'
with open(merged_all_file, 'r', encoding='utf-8') as f:
    merged = json.load(f)

attacks = merged.get('prompt_injections_setup_config', [])
print('='*70)
print('experiment_config.merged_all.json 统计')
print('='*70)
print('总攻击配置数: %d' % len(attacks))

# 按 environment 分类
from collections import Counter
env_cnt = Counter(a.get('environment', '') for a in attacks)
print('\n按 environment 分布:')
for k, v in env_cnt.most_common():
    print('  %s: %d' % (k, v))

# 按 source 分类
src_cnt = Counter(a.get('source', '') for a in attacks)
print('\n按 source 分布:')
for k, v in src_cnt.most_common():
    print('  %s: %d' % (k, v))

# 2. 统计其他额外攻击文件
print('\n' + '='*70)
print('additional_attacks 目录文件统计')
print('='*70)

configs_dir = r'D:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\additional_attacks'
file_stats = {}
for fname in os.listdir(configs_dir):
    if fname.endswith('.json') and not fname.startswith('redteamcua_'):
        fpath = os.path.join(configs_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict):
                count = len(data.get('prompt_injections_setup_config', data.get('attacks', [])))
            else:
                count = 0
            file_stats[fname] = count
        except:
            file_stats[fname] = 'ERR'

# 排除非攻击数据文件
exclude = ['redteamcua_attacks_original.json', 'redteamcua_attacks.json', 'stwebagentbench_original.json']
for k in exclude:
    if k in file_stats:
        del file_stats[k]

print('\n攻击配置文件 (不含 redteamcua_raw):')
for k, v in sorted(file_stats.items(), key=lambda x: -x[1] if isinstance(x[1], int) else 0):
    print('  %s: %s' % (k, v))

# 3. 统计 redteamcua_raw
print('\nredteamcua_raw 文件:')
redteamcua_dir = os.path.join(configs_dir, 'redteamcua_raw')
if os.path.exists(redteamcua_dir):
    total = 0
    for fname in os.listdir(redteamcua_dir):
        if fname.endswith('.json'):
            fpath = os.path.join(redteamcua_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    count = len(data)
                else:
                    count = 1
                total += count
                print('  %s: %d' % (fname, count))
            except:
                print('  %s: ERR' % fname)
    print('  redteamcua_raw 总计: %d' % total)

# 4. 统计 stwebagentbench
print('\nstwebagentbench 目录:')
stweb_dir = os.path.join(configs_dir, 'stwebagentbench')
if os.path.exists(stweb_dir):
    total = 0
    for fname in os.listdir(stweb_dir):
        if fname.endswith('.json') or fname.endswith('.jsonl'):
            fpath = os.path.join(stweb_dir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    if fname.endswith('.jsonl'):
                        data = [json.loads(line) for line in f]
                    else:
                        data = json.load(f)
                if isinstance(data, list):
                    count = len(data)
                else:
                    count = 1
                total += count
                print('  %s: %d' % (fname, count))
            except Exception as e:
                print('  %s: ERR (%s)' % (fname, e))
    print('  stwebagentbench 总计: %d' % total)

# 5. 统计 croissant jsonl
print('\ncroissant jsonl 文件:')
croissant_dir = os.path.join(configs_dir, 'croissant')
if os.path.exists(croissant_dir):
    for fname in ['attacks_in_webarena_format.jsonl', 'utility_in_webarena_format.jsonl']:
        fpath = os.path.join(croissant_dir, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    count = sum(1 for line in f if line.strip())
                print('  %s: %d' % (fname, count))
            except:
                print('  %s: ERR' % fname)

# 6. 统计实际测试结果中各 source 的分布
print('\n' + '='*70)
print('test_output 实际测试结果统计')
print('='*70)
results_file = r'D:\桌面\安全数据\web端\wasp-main-all\test_output\results_summary.json'
if os.path.exists(results_file):
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    results = data.get('results', [])
    print('总测试任务数: %d' % len(results))

    src_cnt = Counter(r.get('source', '') for r in results)
    print('\n按 source 分布:')
    for k, v in src_cnt.most_common():
        print('  %s: %d' % (k, v))

    # 按 result x source 交叉统计
    print('\n按 result x source 交叉统计:')
    cross = {}
    for r in results:
        src = r.get('source', 'unknown')
        res = r.get('result', 'unknown')
        key = (src, res)
        cross[key] = cross.get(key, 0) + 1

    # 找有测试的 source
    tested_sources = sorted(set(k[0] for k in cross.keys()))
    print('%-40s %8s %8s %8s %8s %8s' % ('source', 'pass', 'fail', 'error', 'timeout', 'total'))
    print('-'*80)
    for src in tested_sources:
        pass_c = cross.get((src, 'pass'), 0)
        fail_c = cross.get((src, 'fail'), 0)
        error_c = cross.get((src, 'error'), 0)
        timeout_c = cross.get((src, 'timeout'), 0)
        total_c = pass_c + fail_c + error_c + timeout_c
        print('%-40s %8d %8d %8d %8d %8d' % (src, pass_c, fail_c, error_c, timeout_c, total_c))
