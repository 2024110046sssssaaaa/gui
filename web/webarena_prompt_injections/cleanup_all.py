#!/usr/bin/env python3
"""检查所有数据集的测试状态"""

import os
import glob
import json

# 路径
SAMPLES_DIR = r"D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples"
VWA_LOG_DIR = r"D:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files"

def check_all_samples():
    """检查所有数据集"""
    if not os.path.exists(SAMPLES_DIR):
        print(f"样本目录不存在: {SAMPLES_DIR}")
        return
    
    datasets = sorted(os.listdir(SAMPLES_DIR))
    
    print("=" * 80)
    print("数据集状态概览")
    print("=" * 80)
    
    total_attack_tasks = 0
    total_benign_tasks = 0
    
    for dataset in datasets:
        dataset_path = os.path.join(SAMPLES_DIR, dataset)
        if not os.path.isdir(dataset_path):
            continue
        
        # 统计攻击任务
        attack_dir = os.path.join(dataset_path, "webarena_tasks_attacker")
        benign_dir = os.path.join(dataset_path, "webarena_tasks")
        
        attack_count = 0
        benign_count = 0
        
        if os.path.exists(attack_dir):
            attack_count = len(glob.glob(os.path.join(attack_dir, "*.json")))
            total_attack_tasks += attack_count
        
        if os.path.exists(benign_dir):
            benign_count = len(glob.glob(os.path.join(benign_dir, "*.json")))
            total_benign_tasks += benign_count
        
        # 统计日志
        log_count = len(glob.glob(os.path.join(VWA_LOG_DIR, f"log_*_{dataset}*.log")))
        
        status = "OK"
        if attack_count > 0:
            status = f"{attack_count} 攻击任务"
        
        print(f"  {dataset:40s} | {benign_count:3d} 良性 | {attack_count:3d} 攻击 | {log_count:3d} 日志")
    
    print("=" * 80)
    print(f"总计: {total_benign_tasks} 良性 + {total_attack_tasks} 攻击 = {total_benign_tasks + total_attack_tasks} 任务")
    print()

def delete_all_attacks():
    """删除所有失败的攻击任务配置"""
    if not os.path.exists(SAMPLES_DIR):
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
                    print(f"删除失败 {f}: {e}")
            
            # 如果目录空了，删除目录
            remaining = glob.glob(os.path.join(attack_dir, "*.json"))
            if not remaining:
                try:
                    os.rmdir(attack_dir)
                except:
                    pass
        
        # 删除攻击日志目录
        if os.path.exists(log_dir):
            import shutil
            try:
                shutil.rmtree(log_dir)
                dirs_deleted += 1
                print(f"  删除日志: {dataset}/agent_logs_attacker")
            except Exception as e:
                print(f"  删除日志目录失败: {e}")
    
    print("=" * 80)
    print(f"共删除 {deleted_total} 个攻击任务配置")
    print(f"共删除 {dirs_deleted} 个日志目录")
    print()

if __name__ == "__main__":
    print()
    check_all_samples()
    
    # 询问是否删除
    import shutil
    print("是否删除所有攻击任务配置重新生成？ (y/n)")
    response = input("> ")
    
    if response.lower() == 'y':
        delete_all_attacks()
        print()
        print("下一步：运行以下命令重新生成和测试")
        print()
        print('  cd "d:\\桌面\\安全数据\\web端\\wasp-main-all\\webarena_prompt_injections"')
        print('  python run_all_tests.py --generate')
        print()
        print('或仅生成+测试攻击任务:')
        print('  python run_all_tests.py --generate --attack_only')
