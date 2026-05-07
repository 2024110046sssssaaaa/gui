#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""详细分析攻击任务得分 - 基于 task_id 范围映射"""
import os
import re
import glob
import codecs
from collections import defaultdict

log_dir = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files'

# task_id 范围到数据集的映射（根据实际样本目录）
ID_RANGES = {
    'wa_gitlab_destructive': (3000, 3099),
    'wa_gitlab_data_exfil': (3100, 3199),
    'wa_gitlab_credential_exfil': (5000, 5099),
    'wa_gitlab_ssh_keys': (3300, 3399),
    'wa_gitlab_permissions': (3400, 3499),
    'browserart_suffix': (3540, 3579),
    'browserart_prefix': (3580, 3619),
    'browserart_gcg': (3620, 3659),
    'browserart_attacks_fixed': (3660, 3699),
    'browserart_attacks_enhanced': (3700, 3739),
    'croissant_attacks': (3750, 3761),
}

def get_dataset(task_id):
    try:
        tid = int(task_id)
        for ds, (start, end) in ID_RANGES.items():
            if start <= tid <= end:
                return ds
    except:
        pass
    return 'unknown'

task_scores = {}

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

        match = re.search(r'webarena_tasks_attacker[/\\](\d+)\.json', content)
        if not match:
            continue
        task_id = match.group(1)

        if task_id not in task_scores:
            task_scores[task_id] = score

    except:
        pass

# 统计
total = len(task_scores)
score_1 = sum(1 for s in task_scores.values() if s == 1.0)
score_05 = sum(1 for s in task_scores.values() if s == 0.5)
score_0 = sum(1 for s in task_scores.values() if s == 0.0)

# 按数据集统计
dataset_scores = defaultdict(lambda: {'1.0': 0, '0.5': 0, '0.0': 0, 'total_plan': 0})

# 计划总数
for ds, (start, end) in ID_RANGES.items():
    dataset_scores[ds]['total_plan'] = end - start + 1

for task_id, score in task_scores.items():
    ds = get_dataset(task_id)
    if score == 1.0:
        dataset_scores[ds]['1.0'] += 1
    elif score == 0.5:
        dataset_scores[ds]['0.5'] += 1
    else:
        dataset_scores[ds]['0.0'] += 1

print("=" * 95)
print("Attack Task Results - Summary")
print("=" * 95)
print(f"Total completed: {total}")
print(f"  Score 1.0 (complete success): {score_1} ({round(100*score_1/total, 1) if total else 0}%)")
print(f"  Score 0.5 (partial success): {score_05} ({round(100*score_05/total, 1) if total else 0}%)")
print(f"  Score 0.0 (failed):           {score_0} ({round(100*score_0/total, 1) if total else 0}%)")
print()
print(f"Overall Success Rate (1.0):    {round(100*score_1/total, 1) if total else 0}%")
print(f"Partial+Success Rate (>=0.5):   {round(100*(score_1+score_05)/total, 1) if total else 0}%")

print("\n" + "=" * 95)
print("Per Dataset Breakdown")
print("=" * 95)
print(f"{'Dataset':<35} | {'Done':<6} | {'Plan':<6} | {'1.0':<6} | {'0.5':<6} | {'0.0':<6} | {'Succ%'}")
print("-" * 95)

done_total = 0
plan_total = 0
s1_total = 0
s05_total = 0
s0_total = 0

for ds in sorted(dataset_scores.keys()):
    s = dataset_scores[ds]
    done = s['1.0'] + s['0.5'] + s['0.0']
    plan = s['total_plan']
    success_rate = round(100 * s['1.0'] / done, 1) if done > 0 else 0

    done_total += done
    plan_total += plan
    s1_total += s['1.0']
    s05_total += s['0.5']
    s0_total += s['0.0']

    print(f"{ds:<35} | {done:<6} | {plan:<6} | {s['1.0']:<6} | {s['0.5']:<6} | {s['0.0']:<6} | {success_rate}%")

print("-" * 95)
overall_succ = round(100 * s1_total / done_total, 1) if done_total > 0 else 0
print(f"{'TOTAL':<35} | {done_total:<6} | {plan_total:<6} | {s1_total:<6} | {s05_total:<6} | {s0_total:<6} | {overall_succ}%")

print("\n" + "=" * 95)
print("Legend")
print("=" * 95)
print("  Score 1.0: Task completed successfully")
print("  Score 0.5: Task partially completed")
print("  Score 0.0: Task failed")
print("  Succ%: Percentage of completed tasks that scored 1.0")
print("  Done: Number of tasks with results")
print("  Plan: Total planned tasks")
