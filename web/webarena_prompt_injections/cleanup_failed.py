#!/usr/bin/env python3
"""清理失败的测试样本并重新生成"""

import os
import glob
import json
import shutil

# 设置路径
SAMPLES_DIR = r"D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples"
VWA_LOG_DIR = r"D:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files"
FAILED_TASKS = []

# 扫描日志找出所有 Average score: 0.0 的任务
log_files = glob.glob(os.path.join(VWA_LOG_DIR, "log_*.log"))
for log_file in log_files:
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if 'Average score: 0.0' in content:
                # 找到任务配置路径
                for line in content.split('\n'):
                    if '[Config file]' in line or '[Result]' in line:
                        # 提取 JSON 文件路径
                        import re
                        match = re.search(r'(?:Config file|Result].*?)(.*?webarena_tasks[_\w]+\\[\d]+\.json)', line)
                        if match:
                            task_path = match.group(1)
                            # 转换路径分隔符
                            task_path = task_path.replace('/', '\\')
                            FAILED_TASKS.append(task_path)
                            break
    except Exception as e:
        print(f"Error reading {log_file}: {e}")

# 去重
FAILED_TASKS = list(set(FAILED_TASKS))
print(f"找到 {len(FAILED_TASKS)} 个失败的任务")

# 删除失败任务对应的配置文件
deleted_count = 0
for task_path in FAILED_TASKS:
    # 处理路径中的编码问题，尝试多种方式
    task_path_variants = [
        task_path,
        task_path.replace('\\', '/'),
        task_path.replace('\u5b89\u5168\u6570\u636e', '安全数据'),
    ]
    
    for variant in task_path_variants:
        if os.path.exists(variant):
            try:
                os.remove(variant)
                print(f"删除: {variant}")
                deleted_count += 1
                break
            except Exception as e:
                print(f"删除失败 {variant}: {e}")

print(f"\n共删除了 {deleted_count} 个任务配置文件")
print("\n现在需要重新生成样本并测试")
print("运行命令:")
print('  cd "d:\\桌面\\安全数据\\web端\\wasp-main-all\\webarena_prompt_injections"')
print("  python run_all_tests.py --generate --filter_source browserart_attacks_enhanced")
