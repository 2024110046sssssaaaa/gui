#!/usr/bin/env python3
"""重新生成 browserart_attacks_enhanced 样本"""

import sys
import os
import glob
import json

# 添加路径
sys.path.insert(0, r'D:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections')

from run_all_tests import generate_test_samples, DATA_SOURCES, configs_dir
import argparse

def main():
    # 创建参数
    args = argparse.Namespace(
        mode='generate',
        sample_dir=None,
        output_dir=None,
        generate_only=True,
        max_tests=0,
        filter_source='browserart_attacks_enhanced',
        filter_env='gitlab',
        attack_only=False,
        benign_only=False,
        resume=None,
        skip_pass=True
    )

    output_base = r'D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all'
    
    print("=" * 60)
    print("重新生成 browserart_attacks_enhanced 样本")
    print("=" * 60)
    print()
    
    samples_dir = generate_test_samples(output_base, args)

    print()
    print("=" * 60)
    print("样本生成完成！")
    print("=" * 60)
    print(f"样本目录: {samples_dir}")

    # 检查生成的文件
    attacker_dir = os.path.join(samples_dir, 'browserart_attacks_enhanced', 'webarena_tasks_attacker')
    if os.path.exists(attacker_dir):
        files = glob.glob(os.path.join(attacker_dir, '*.json'))
        print(f"生成攻击任务: {len(files)} 个")
        
        # 检查第一个文件是否有正确的 URL
        if files:
            with open(files[0], 'r', encoding='utf-8') as f:
                task = json.load(f)
            print()
            print("第一个任务验证:")
            print(f"  action_url: {task.get('action_url', 'N/A')}")
            print(f"  start_url: {task.get('start_url', 'N/A')}")
            print(f"  project_owner: {task.get('parameters', {}).get('project_owner', 'N/A')}")
            
            # 检查 URL 是否还有未替换的变量
            action_url = task.get('action_url', '')
            if '{project_owner}' in action_url or '{project_name}' in action_url:
                print()
                print("  [警告] URL 中仍有未替换的变量!")
            else:
                print()
                print("  [OK] URL 已正确替换")

if __name__ == '__main__':
    main()
