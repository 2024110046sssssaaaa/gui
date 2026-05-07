import json
import re

# 文件路径
utility_file = r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\croissant\utility_in_webarena_format.jsonl'
attacks_file = r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\croissant\attacks_in_webarena_format.jsonl'
exp_config_file = r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\experiment_config.raw.json'

print("开始批量修改配置文件...")
print("=" * 60)

# ==================== 处理 utility_in_webarena_format.jsonl ====================
print("\n1. 处理 utility_in_webarena_format.jsonl")
print("-" * 60)

with open(utility_file, 'r', encoding='utf-8') as f:
    utility_lines = f.readlines()

utility_modified_count = 0
for i, line in enumerate(utility_lines):
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
        # utility文件使用sites字段，值为["gitlab"]
        is_gitlab = obj.get('environment') == 'gitlab' or ('sites' in obj and 'gitlab' in obj.get('sites', []))
        if is_gitlab:
            project_name = obj.get('parameters', {}).get('project_name')
            task_id = obj.get('task_id')
            if task_id and task_id >= 3000:
                variant_num = str(task_id - 2999).zfill(3)
                if project_name == 'dotfiles':
                    old = obj['parameters']['project_name']
                    obj['parameters']['project_name'] = f'dotfiles_gitlab_{variant_num}'
                    # 更新 parameters_str
                    params = obj['parameters'].copy()
                    obj['parameters_str'] = str(params)
                    utility_lines[i] = json.dumps(obj, ensure_ascii=False) + '\n'
                    print(f"  [行{i+1}] task_id={task_id}: '{old}' -> '{obj['parameters']['project_name']}'")
                    utility_modified_count += 1
                elif project_name == 'a11yproject.com':
                    old = obj['parameters']['project_name']
                    obj['parameters']['project_name'] = f'a11yproject_gitlab_{variant_num}'
                    params = obj['parameters'].copy()
                    obj['parameters_str'] = str(params)
                    utility_lines[i] = json.dumps(obj, ensure_ascii=False) + '\n'
                    print(f"  [行{i+1}] task_id={task_id}: '{old}' -> '{obj['parameters']['project_name']}'")
                    utility_modified_count += 1
    except json.JSONDecodeError as e:
        print(f"  警告：第{i+1}行JSON解析失败: {e}")

    if utility_modified_count > 0:
        with open(utility_file, 'w', encoding='utf-8') as f:
            f.writelines(utility_lines)
        print(f"\n[OK] 已保存 {utility_file}，共修改 {utility_modified_count} 个条目")
    else:
        print(f"\n[OK] 无需修改 {utility_file}")

# ==================== 处理 attacks_in_webarena_format.jsonl ====================
print("\n2. 处理 attacks_in_webarena_format.jsonl")
print("-" * 60)

with open(attacks_file, 'r', encoding='utf-8') as f:
    attacks_lines = f.readlines()

# attacks文件没有task_id，按GitLab条目出现的顺序分配
gitlab_count = 0
attacks_modified_count = 0

for i, line in enumerate(attacks_lines):
    line = line.strip()
    if not line:
        continue
    try:
        obj = json.loads(line)
        if obj.get('environment') == 'gitlab':
            gitlab_count += 1
            project_name = obj.get('parameters', {}).get('project_name')
            # 按出现顺序分配task_id: 从3000开始
            task_id = 3000 + gitlab_count - 1
            variant_num = str(task_id - 2999).zfill(3)
            
            if project_name == 'dotfiles':
                old = obj['parameters']['project_name']
                obj['parameters']['project_name'] = f'dotfiles_gitlab_{variant_num}'
                # 更新 parameters_str
                params = obj['parameters'].copy()
                obj['parameters_str'] = str(params)
                attacks_lines[i] = json.dumps(obj, ensure_ascii=False) + '\n'
                print(f"  [行{i+1}] GitLab#{gitlab_count} (task_id={task_id}): '{old}' -> '{obj['parameters']['project_name']}'")
                attacks_modified_count += 1
            elif project_name == 'a11yproject.com':
                old = obj['parameters']['project_name']
                obj['parameters']['project_name'] = f'a11yproject_gitlab_{variant_num}'
                params = obj['parameters'].copy()
                obj['parameters_str'] = str(params)
                attacks_lines[i] = json.dumps(obj, ensure_ascii=False) + '\n'
                print(f"  [行{i+1}] GitLab#{gitlab_count} (task_id={task_id}): '{old}' -> '{obj['parameters']['project_name']}'")
                attacks_modified_count += 1
    except json.JSONDecodeError as e:
        print(f"  警告：第{i+1}行JSON解析失败: {e}")

    if attacks_modified_count > 0:
        with open(attacks_file, 'w', encoding='utf-8') as f:
            f.writelines(attacks_lines)
        print(f"\n[OK] 已保存 {attacks_file}，共修改 {attacks_modified_count} 个条目")
    else:
        print(f"\n[OK] 无需修改 {attacks_file}")

# ==================== 处理 experiment_config.raw.json ====================
print("\n3. 处理 experiment_config.raw.json")
print("-" * 60)

with open(exp_config_file, 'r', encoding='utf-8') as f:
    exp_content = f.read()

# 查找所有GitLab相关的project_name
lines = exp_content.split('\n')
total_modified = 0

for idx, line in enumerate(lines):
    # 检查是否是project_name行且值为dotfiles或a11yproject.com
    if '"project_name":' in line:
        # 查找对应的variant信息（需要在前面找）
        variant_num = None
        for j in range(idx-1, max(idx-20, 0), -1):
            if 'free_form_name' in lines[j]:
                match = re.search(r'variant\s+(\d+)', lines[j])
                if match:
                    variant_num = match.group(1)
                    break
        
        if variant_num and ('"dotfiles"' in line or '"a11yproject.com"' in line):
            if '"dotfiles"' in line:
                old_line = line
                new_line = line.replace('"dotfiles"', f'"dotfiles_gitlab_{variant_num}"')
                lines[idx] = new_line
                print(f"  [行{idx+1}] variant {variant_num}: dotfiles -> dotfiles_gitlab_{variant_num}")
                total_modified += 1
            elif '"a11yproject.com"' in line:
                old_line = line
                new_line = line.replace('"a11yproject.com"', f'"a11yproject_gitlab_{variant_num}"')
                lines[idx] = new_line
                print(f"  [行{idx+1}] variant {variant_num}: a11yproject.com -> a11yproject_gitlab_{variant_num}")
                total_modified += 1

    if total_modified > 0:
        new_content = '\n'.join(lines)
        with open(exp_config_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"\n[OK] 已保存 {exp_config_file}，共修改 {total_modified} 个条目")
    else:
        print(f"\n[OK] 无需修改 {exp_config_file}")

print("\n" + "=" * 60)
print(f"修改完成！")
print(f"  utility_in_webarena_format.jsonl: {utility_modified_count} 个修改")
print(f"  attacks_in_webarena_format.jsonl: {attacks_modified_count} 个修改")
print(f"  experiment_config.raw.json: {total_modified} 个修改")
print(f"  总计: {utility_modified_count + attacks_modified_count + total_modified} 个修改")
