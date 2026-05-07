#!/usr/bin/env python3
"""重新生成所有攻击任务样本"""

import sys
import os
import glob
import json

sys.path.insert(0, r'D:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections')

from run_all_tests import generate_test_samples
import argparse

def main():
    args = argparse.Namespace(
        mode='generate',
        sample_dir=None,
        output_dir=None,
        generate_only=True,
        max_tests=0,
        filter_source=None,  # 所有数据源
        filter_env='gitlab',
        attack_only=False,
        benign_only=False,
        resume=None,
        skip_pass=True
    )

    output_base = r'D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all'
    
    print("=" * 80)
    print("重新生成所有攻击任务样本")
    print("=" * 80)
    print()
    
    samples_dir = generate_test_samples(output_base, args)

    print()
    print("=" * 80)
    print("样本生成完成！")
    print("=" * 80)
    
    # 统计生成的任务
    total_attack = 0
    datasets_info = []
    
    for dataset in os.listdir(samples_dir):
        dataset_path = os.path.join(samples_dir, dataset)
        if not os.path.isdir(dataset_path):
            continue
        
        attack_dir = os.path.join(dataset_path, "webarena_tasks_attacker")
        if os.path.exists(attack_dir):
            count = len(glob.glob(os.path.join(attack_dir, "*.json")))
            total_attack += count
            datasets_info.append((dataset, count))
    
    print()
    print("生成的攻击任务统计:")
    for dataset, count in datasets_info:
        print(f"  {dataset:40s}: {count:3d} 个")
    print(f"  {'总计':40s}: {total_attack:3d} 个")
    print()

if __name__ == '__main__':
    main()
