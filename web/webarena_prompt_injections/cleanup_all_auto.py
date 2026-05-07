#!/usr/bin/env python3
"""删除所有失败的攻击任务配置"""

import os
import glob
import shutil

SAMPLES_DIR = r"D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples"

def delete_all_attacks():
    """删除所有攻击任务配置和日志目录"""
    if not os.path.exists(SAMPLES_DIR):
        print(f"样本目录不存在: {SAMPLES_DIR}")
        return
    
    datasets = sorted(os.listdir(SAMPLES_DIR))
    
    deleted_total = 0
    dirs_deleted = 0
    
    print("=" * 80)
    print("删除所有攻击任务配置和日志目录")
    print("=" * 80)
    
    for dataset in datasets:
        dataset_path = os.path.join(SAMPLES_DIR, dataset)
        if not os.path.isdir(dataset_path):
            continue
        
        attack_dir = os.path.join(dataset_path, "webarena_tasks_attacker")
        log_dir = os.path.join(dataset_path, "agent_logs_attacker")
        
        # 删除攻击任务配置
        if os.path.exists(attack_dir):
            files = glob.glob(os.path.join(attack_dir, "*.json"))
            for f in files:
                try:
                    os.remove(f)
                    deleted_total += 1
                except Exception as e:
                    pass
            
            # 删除空目录
            remaining = glob.glob(os.path.join(attack_dir, "*.json"))
            if not remaining:
                try:
                    os.rmdir(attack_dir)
                except:
                    pass
        
        # 删除攻击日志目录
        if os.path.exists(log_dir):
            try:
                shutil.rmtree(log_dir)
                dirs_deleted += 1
                print(f"  删除日志: {dataset}/agent_logs_attacker")
            except Exception as e:
                pass
    
    print("=" * 80)
    print(f"共删除 {deleted_total} 个攻击任务配置")
    print(f"共删除 {dirs_deleted} 个日志目录")
    print()

if __name__ == "__main__":
    delete_all_attacks()
    print()
    print("=" * 80)
    print("下一步：运行以下命令重新生成和测试")
    print("=" * 80)
    print()
    print('  cd "d:\\桌面\\安全数据\\web端\\wasp-main-all\\webarena_prompt_injections"')
    print('  python run_all_tests.py --generate --attack_only')
