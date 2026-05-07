#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug script"""
import os
import re
import glob
import codecs

log_dir = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files'

# 列出最近有结果的日志
log_files = glob.glob(os.path.join(log_dir, 'log_*.log'))

found_scores = 0
found_tasks = 0
both_found = 0

for log_file in log_files[:100]:  # 只检查前100个
    try:
        with codecs.open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        score_match = re.search(r'Average score:\s*([\d.]+)', content)
        filename = os.path.basename(log_file)
        task_match = re.search(r'log_\d+_\d+_(\d+)\.log', filename)
        
        has_webarena = 'webarena_tasks' in content
        
        if score_match:
            found_scores += 1
        if task_match:
            found_tasks += 1
        if score_match and task_match:
            both_found += 1
            
    except Exception as e:
        pass

print(f"Checked first 100 files:")
print(f"  Files with 'Average score': {found_scores}")
print(f"  Files with task_id in filename: {found_tasks}")
print(f"  Files with both: {both_found}")

# 列出最近有Average score的日志
print("\nRecent logs with Average score:")
count = 0
for log_file in sorted(log_files, key=os.path.getmtime, reverse=True):
    try:
        with codecs.open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        score_match = re.search(r'Average score:\s*([\d.]+)', content)
        if score_match and 'gitlab_tests_all' in content:
            filename = os.path.basename(log_file)
            task_match = re.search(r'log_\d+_\d+_(\d+)\.log', filename)
            role = 'attacker' if 'webarena_tasks_attacker' in content else ('benign' if 'webarena_tasks' in content else 'unknown')
            print(f"  {filename}: score={score_match.group(1)}, task_id={task_match.group(1) if task_match else 'N/A'}, role={role}")
            count += 1
            if count >= 10:
                break
    except:
        pass
