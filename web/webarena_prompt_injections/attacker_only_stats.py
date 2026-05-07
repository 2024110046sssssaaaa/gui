#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只统计攻击任务的成功率"""
import os
import re
import glob
import codecs
from collections import defaultdict

# 配置路径
samples_dir = r'd:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples'
log_dir = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files'

# 统计攻击任务结果
attacker_results = {}  # task_id -> score
dataset_stats = defaultdict(lambda: {'total': 0, 'done': 0, 'score_1': 0, 'score_05': 0, 'score_0': 0, 'error': 0, 'timeout': 0})

# 扫描 samples 目录
for sample_dir in glob.glob(os.path.join(samples_dir, '*')):
    dataset_name = os.path.basename(sample_dir)

    # 只扫描攻击任务
    attacker_dir = os.path.join(sample_dir, 'webarena_tasks_attacker')
    if not os.path.isdir(attacker_dir):
        continue

    attacker_tasks = glob.glob(os.path.join(attacker_dir, '*.json'))
    dataset_stats[dataset_name]['total'] = len(attacker_tasks)

    for task_file in attacker_tasks:
        task_id = os.path.splitext(os.path.basename(task_file))[0]
        logs_dir = os.path.join(sample_dir, 'agent_logs_attacker')

        score = None
        status = 'no_log'

        # 查找对应的 .log 文件
        log_file = os.path.join(logs_dir, f'render_{task_id}.log')
        if os.path.exists(log_file):
            try:
                with codecs.open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                if 'Average score: 1.0' in content:
                    score = 1.0
                    status = 'score_1'
                elif 'Average score: 0.5' in content:
                    score = 0.5
                    status = 'score_05'
                elif 'Average score: 0.0' in content:
                    score = 0.0
                    status = 'score_0'
                elif 'timeout' in content.lower():
                    status = 'timeout'
                else:
                    status = 'error'
            except:
                status = 'error'

        if score is not None:
            attacker_results[task_id] = score
            dataset_stats[dataset_name]['done'] += 1

        if status != 'no_log':
            dataset_stats[dataset_name][status] += 1

# 也从 visualwebarena/log_files 补充
for log_file in glob.glob(os.path.join(log_dir, 'log_*.log')):
    try:
        with codecs.open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        # 只处理攻击任务
        if 'webarena_tasks_attacker' not in content:
            continue

        score_match = re.search(r'Average score:\s*([\d.]+)', content)
        if not score_match:
            continue
        score = float(score_match.group(1))

        config_match = re.search(r'webarena_tasks_attacker[/\\](\d+)\.json', content)
        if not config_match:
            continue
        task_id = config_match.group(1)

        if task_id not in attacker_results:
            attacker_results[task_id] = score

    except:
        pass

# 计算成功率
total_attacker = sum(s['total'] for s in dataset_stats.values())
done_attacker = len(attacker_results)

score_1 = sum(1 for s in attacker_results.values() if s == 1.0)
score_05 = sum(1 for s in attacker_results.values() if s == 0.5)
score_0 = sum(1 for s in attacker_results.values() if s == 0.0)

print("=" * 80)
print("攻击任务统计（不看良性任务）")
print("=" * 80)

print(f"\n{'数据源':<30} | {'完成/总数':<12} | {'1.0分':<8} | {'0.5分':<8} | {'0.0分':<8}")
print("-" * 80)
for name in sorted(dataset_stats.keys()):
    stats = dataset_stats[name]
    if stats['total'] > 0:
        print(f"{name:<30} | {stats['done']}/{stats['total']:<10} | {stats['score_1']:<8} | {stats['score_05']:<8} | {stats['score_0']:<8}")

print("-" * 80)
print(f"{'总计':<30} | {done_attacker}/{total_attacker:<10} | {score_1:<8} | {score_05:<8} | {score_0:<8}")

print("\n" + "=" * 80)
print("攻击成功率分析")
print("=" * 80)
print(f"已完成攻击任务: {done_attacker}")
print(f"未完成攻击任务: {total_attacker - done_attacker}")
print()
print(f"完全成功 (score = 1.0): {score_1} / {done_attacker} = {round(100*score_1/done_attacker, 1) if done_attacker else 0}%")
print(f"部分成功 (score = 0.5): {score_05} / {done_attacker} = {round(100*score_05/done_attacker, 1) if done_attacker else 0}%")
print(f"完全失败 (score = 0.0): {score_0} / {done_attacker} = {round(100*score_0/done_attacker, 1) if done_attacker else 0}%")

# 按数据集统计成功率
print("\n" + "=" * 80)
print("各数据集攻击成功率")
print("=" * 80)
for name in sorted(dataset_stats.keys()):
    stats = dataset_stats[name]
    if stats['done'] > 0:
        rate = round(100 * stats['score_1'] / stats['done'], 1)
        print(f"  {name}: {rate}% ({stats['score_1']}/{stats['done']})")
