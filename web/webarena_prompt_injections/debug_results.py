#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析测试结果 - Debug版本"""
import os
import re
import glob

log_dir = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files'
samples_dir = r'd:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples'

# 调试: 列出最近修改的日志文件
log_files = glob.glob(os.path.join(log_dir, 'log_*.log'))
log_files_sorted = sorted(log_files, key=os.path.getmtime, reverse=True)

print(f"Total log files: {len(log_files)}")
print(f"Recent log files (top 5):")
for f in log_files_sorted[:5]:
    print(f"  {os.path.basename(f)} - {os.path.getmtime(f)}")

# 从最新的日志文件测试读取
print("\nTesting read from most recent log:")
test_file = log_files_sorted[0]
try:
    with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    print(f"  File size: {len(content)} chars")
    print(f"  Content preview: {content[:500]}")
    
    # 测试正则
    score_match = re.search(r'Average score:\s*([\d.]+)', content)
    print(f"  Score match: {score_match}")
    
    filename = os.path.basename(test_file)
    task_match = re.search(r'log_\d+_\d+_(\d+)\.log', filename)
    print(f"  Task match: {task_match}")
    
    print(f"  'webarena_tasks' in content: {'webarena_tasks' in content}")
    print(f"  'webarena_tasks_attacker' in content: {'webarena_tasks_attacker' in content}")
except Exception as e:
    print(f"  Error: {e}")
