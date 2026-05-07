#!/usr/bin/env python3
"""删除 browserart_attacks_enhanced 中失败的任务并重新生成"""

import os
import glob
import shutil

# 路径
SAMPLES_DIR = r"D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples\browserart_attacks_enhanced"
ATTACKER_TASKS_DIR = os.path.join(SAMPLES_DIR, "webarena_tasks_attacker")
ATTACKER_LOGS_DIR = os.path.join(SAMPLES_DIR, "agent_logs_attacker")

def delete_failed_attacks():
    """删除所有攻击任务（因为它们都失败了）"""
    
    deleted = 0
    
    # 删除攻击任务配置文件
    if os.path.exists(ATTACKER_TASKS_DIR):
        task_files = glob.glob(os.path.join(ATTACKER_TASKS_DIR, "*.json"))
        for f in task_files:
            try:
                os.remove(f)
                deleted += 1
            except Exception as e:
                print(f"删除失败 {f}: {e}")
    
    # 删除攻击日志目录
    if os.path.exists(ATTACKER_LOGS_DIR):
        try:
            shutil.rmtree(ATTACKER_LOGS_DIR)
            print(f"删除目录: {ATTACKER_LOGS_DIR}")
        except Exception as e:
            print(f"删除目录失败: {e}")
    
    print(f"共删除 {deleted} 个攻击任务配置")
    return deleted

if __name__ == "__main__":
    print("=" * 60)
    print("清理 browserart_attacks_enhanced 失败的攻击任务")
    print("=" * 60)
    print(f"\n攻击任务目录: {ATTACKER_TASKS_DIR}")
    print(f"攻击日志目录: {ATTACKER_LOGS_DIR}")
    print()
    
    count = delete_failed_attacks()
    
    print()
    print("=" * 60)
    print("清理完成！")
    print("=" * 60)
    print()
    print("下一步：重新生成样本并测试")
    print()
    print('运行命令:')
    print('  cd "d:\\桌面\\安全数据\\web端\\wasp-main-all\\webarena_prompt_injections"')
    print('  python run_all_tests.py --generate --filter_source browserart_attacks_enhanced')
    print()
    print('或者一步完成生成+测试:')
    print('  python run_all_tests.py --generate --filter_source browserart_attacks_enhanced --run')
