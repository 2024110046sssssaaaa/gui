#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""详细分析攻击任务得分 - 修复版"""
import os
import re
import glob
import codecs
from collections import defaultdict

log_dir = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files'

task_scores = {}
task_datasets = {}

for log_file in glob.glob(os.path.join(log_dir, 'log_*.log')):
    try:
        with codecs.open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        if 'webarena_tasks_attacker' not in content:
            continue

        score_match = re.search(r'Average score:\s*([\d.]+)', content)
        if not score_match:
            continue
        score = float(score_match.group(1))

        # 更精确地匹配 task_id
        match = re.search(r'webarena_tasks_attacker[/\\](\d+)\.json', content)
        if not match:
            continue
        task_id = match.group(1)

        # 提取数据集名 - 多种模式
        # samples/xxx/webarena_tasks_attacker/xxx.json
        # samples\xxx\webarena_tasks_attacker\xxx.json
        ds_match = re.search(r'samples[/\\]([^/\\]+)[/\\]webarena_tasks_attacker', content)
        if ds_match:
            dataset = ds_match.group(1)
        else:
            # 尝试从 Config file 完整路径提取
            config_match = re.search(r'\\samples\\([^\\]+)\\webarena_tasks_attacker', content)
            if config_match:
                dataset = config_match.group(1)
            else:
                dataset = 'unknown'

        if task_id not in task_scores:
            task_scores[task_id] = score
            task_datasets[task_id] = dataset

    except:
        pass

# 统计
total = len(task_scores)
score_1 = sum(1 for s in task_scores.values() if s == 1.0)
score_05 = sum(1 for s in task_scores.values() if s == 0.5)
score_0 = sum(1 for s in task_scores.values() if s == 0.0)

# 按数据集统计
dataset_scores = defaultdict(lambda: {'1.0': 0, '0.5': 0, '0.0': 0})
for task_id, score in task_scores.items():
    ds = task_datasets.get(task_id, 'unknown')
    if score == 1.0:
        dataset_scores[ds]['1.0'] += 1
    elif score == 0.5:
        dataset_scores[ds]['0.5'] += 1
    else:
        dataset_scores[ds]['0.0'] += 1

print("=" * 85)
print("Attack Task Results (Attacker Scores Only)")
print("=" * 85)
print(f"Total completed: {total}")
print(f"  Score 1.0 (complete success): {score_1} ({round(100*score_1/total, 1) if total else 0}%)")
print(f"  Score 0.5 (partial success): {score_05} ({round(100*score_05/total, 1) if total else 0}%)")
print(f"  Score 0.0 (failed):           {score_0} ({round(100*score_0/total, 1) if total else 0}%)")
print()
print(f"Overall Success Rate (1.0): {round(100*score_1/total, 1) if total else 0}%")
print(f"Partial+Success Rate (>=0.5): {round(100*(score_1+score_05)/total, 1) if total else 0}%")

print("\n" + "=" * 85)
print("Per Dataset Breakdown")
print("=" * 85)
print(f"{'Dataset':<35} | {'1.0':<6} | {'0.5':<6} | {'0.0':<6} | {'Total':<6} | {'1.0%'}")
print("-" * 85)
for ds in sorted(dataset_scores.keys()):
    s = dataset_scores[ds]
    t = s['1.0'] + s['0.5'] + s['0.0']
    success_rate = round(100 * s['1.0'] / t, 1) if t > 0 else 0
    print(f"{ds:<35} | {s['1.0']:<6} | {s['0.5']:<6} | {s['0.0']:<6} | {t:<6} | {success_rate}%")

# 打印 unknown 的详情用于调试
unknown_tasks = [(tid, task_datasets[tid]) for tid in task_datasets if task_datasets[tid] == 'unknown'][:5]
if unknown_tasks:
    print("\nDebug - sample unknown tasks:", unknown_tasks[:3])
