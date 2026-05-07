#!/usr/bin/env python3
"""
批量修改GitLab攻击数据文件中的项目名称，确保每个攻击使用独立项目
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

# 需要处理的文件列表
TARGET_FILES = [
    "configs/additional_attacks/wa_gitlab_ssh_keys.json",
    "configs/additional_attacks/wa_gitlab_permissions.json",
    "configs/additional_attacks/wa_gitlab_destructive.json",
    "configs/additional_attacks/wa_gitlab_data_exfil.json",
    "configs/additional_attacks/wa_gitlab_credential_exfil.json",
    "configs/experiment_config.merged_all.json",
]

def extract_variant_number(free_form_name: str) -> str:
    """从free_form_name中提取variant编号，如'variant 001' -> '001'"""
    match = re.search(r'variant\s+(\d+)', free_form_name)
    if match:
        return match.group(1).zfill(3)
    return None

def generate_unique_project_name(original_name: str, free_form_name: str) -> str:
    """生成唯一的项目名称"""
    variant_num = extract_variant_number(free_form_name)
    if not variant_num:
        return original_name  # 如果没有variant编号，保持原样
    
    if original_name == "dotfiles":
        return f"dotfiles_gitlab_{variant_num}"
    elif original_name == "a11yproject.com":
        return f"a11yproject_gitlab_{variant_num}"
    else:
        return original_name  # 其他项目名保持不变

def process_config_file(filepath: Path) -> Tuple[int, int]:
    """
    处理单个配置文件
    返回: (修改的条目数, 扫描的总条目数)
    """
    print(f"\n处理文件: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  错误: 无法读取文件 - {e}")
        return (0, 0)
    
    if 'prompt_injections_setup_config' not in data:
        print(f"  跳过: 不是有效的攻击配置文件")
        return (0, 0)
    
    total_entries = len(data['prompt_injections_setup_config'])
    modified_count = 0
    gitlab_entries = 0
    
    for entry in data['prompt_injections_setup_config']:
        # 只处理GitLab环境
        if entry.get('environment') != 'gitlab':
            continue
        
        gitlab_entries += 1
        
        # 检查是否有project_name参数
        if 'parameters' not in entry or 'project_name' not in entry['parameters']:
            continue
        
        original_project = entry['parameters']['project_name']
        
        # 只处理dotfiles和a11yproject.com
        if original_project not in ['dotfiles', 'a11yproject.com']:
            continue
        
        # 检查setup_fn: 如果为空字符串，表示使用现有项目，应该修改
        # 如果setup_fn不为空，表示会创建新项目，也应该修改以避免冲突
        # 根据需求："不要修改 setup_fn 为空的项目" - 我们理解为如果setup_fn为空则保持原样
        setup_fn = entry.get('setup_fn', '')
        if setup_fn == '':
            print(f"  跳过: setup_fn为空，使用现有项目 - {entry.get('free_form_name', 'Unknown')}")
            continue
        
        # 生成新的项目名称
        new_project = generate_unique_project_name(
            original_project,
            entry.get('free_form_name', '')
        )
        
        if new_project != original_project:
            # 修改parameters中的project_name
            entry['parameters']['project_name'] = new_project
            modified_count += 1
            print(f"  修改: {original_project} -> {new_project}")
            print(f"    free_form_name: {entry.get('free_form_name', 'Unknown')}")
    
    # 保存修改后的文件
    if modified_count > 0:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"  已保存，修改了 {modified_count}/{gitlab_entries} 个GitLab条目")
        except Exception as e:
            print(f"  错误: 无法保存文件 - {e}")
    else:
        print(f"  无需修改（扫描了 {gitlab_entries} 个GitLab条目）")
    
    return (modified_count, total_entries)

def main():
    """主函数"""
    base_dir = Path.cwd()
    
    print("=" * 60)
    print("GitLab攻击项目名称批量修改工具")
    print("=" * 60)
    
    total_modified = 0
    total_scanned = 0
    processed_files = 0
    
    for file_path_str in TARGET_FILES:
        filepath = base_dir / file_path_str
        if not filepath.exists():
            print(f"\n文件不存在，跳过: {filepath}")
            continue
        
        modified, scanned = process_config_file(filepath)
        total_modified += modified
        total_scanned += scanned
        processed_files += 1
    
    print("\n" + "=" * 60)
    print(f"处理完成!")
    print(f"处理文件数: {processed_files}")
    print(f"总修改条目: {total_modified}")
    print(f"总扫描条目: {total_scanned}")
    print("=" * 60)
    
    return total_modified

if __name__ == "__main__":
    sys.exit(main())
