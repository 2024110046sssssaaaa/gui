# -*- coding: utf-8 -*-
import json
import os
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8')

# 读取results_summary.json
with open('test_output/results_summary.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# 筛选GitLab相关的任务
print('=== GitLab任务分析 ===\n')

# 检查result目录中的render文件来确认环境
gitlab_tasks = []
for r in results['results']:
    task_id = r.get('task_id')
    result_dir = f'test_output/result_{task_id}'
    render_file = os.path.join(result_dir, f'render_{task_id}.html')
    
    if os.path.exists(render_file):
        with open(render_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        if 'environment: gitlab' in content or 'gitlab' in r.get('source', '').lower():
            gitlab_tasks.append(r)

print(f'GitLab相关任务总数: {len(gitlab_tasks)}')

# 统计GitLab任务的状态分布
status_counts = {}
for r in gitlab_tasks:
    status = r.get('result', 'unknown')
    status_counts[status] = status_counts.get(status, 0) + 1

print('\n状态分布:')
for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f'  {status}: {count}')

# 分析GitLab的error
print('\n=== GitLab Error 分析 ===\n')
gitlab_errors = [r for r in gitlab_tasks if r.get('result') == 'error']
print(f'GitLab error任务数: {len(gitlab_errors)}')

# 检查error任务的来源
error_by_source = {}
for r in gitlab_errors:
    source = r.get('source', 'unknown')
    error_by_source[source] = error_by_source.get(source, 0) + 1

print('Error来源分布:')
for source, count in sorted(error_by_source.items(), key=lambda x: -x[1]):
    print(f'  {source}: {count}')

# 检查具体error任务的日志
print('\n=== 检查GitLab error任务的具体情况 ===\n')
for r in gitlab_errors[:10]:
    task_id = r.get('task_id')
    result_dir = f'test_output/result_{task_id}'
    
    # 检查日志文件
    log_files_txt = os.path.join(result_dir, 'log_files.txt')
    if os.path.exists(log_files_txt):
        with open(log_files_txt, 'r', encoding='utf-8') as f:
            log_path = f.read().strip()
        full_log = os.path.join('visualwebarena', log_path)
        
        if os.path.exists(full_log):
            size = os.path.getsize(full_log)
            with open(full_log, 'rb') as f:
                content = f.read()
            
            has_avg_score = b'Average score' in content
            has_result = b'[Result]' in content
            has_openai_error = b'OpenAI Error' in content
            
            print(f'Task {task_id}: {size} bytes, score={has_avg_score}, result={has_result}, openai_error={has_openai_error}')
        else:
            print(f'Task {task_id}: Log file not found')
    else:
        print(f'Task {task_id}: No log_files.txt')

# 分析成功的攻击
print('\n' + '='*60)
print('=== GitLab 攻击成功 案例分析 ===')
print('='*60 + '\n')

gitlab_success = [r for r in gitlab_tasks if r.get('result') == 'pass']
print(f'GitLab攻击成功任务数: {len(gitlab_success)}')

if gitlab_success:
    # 找一个成功的任务，详细分析
    success_task = gitlab_success[0]
    task_id = success_task.get('task_id')
    result_dir = f'test_output/result_{task_id}'
    
    print(f'\n=== 成功案例 Task {task_id} ===')
    print(f'名称: {success_task.get("name")}')
    print(f'来源: {success_task.get("source")}')
    
    # 检查日志
    log_files_txt = os.path.join(result_dir, 'log_files.txt')
    if os.path.exists(log_files_txt):
        with open(log_files_txt, 'r', encoding='utf-8') as f:
            log_path = f.read().strip()
        full_log = os.path.join('visualwebarena', log_path)
        
        if os.path.exists(full_log):
            with open(full_log, 'rb') as f:
                content = f.read()
            print(f'\n日志内容 ({len(content)} bytes):')
            print(content.decode('utf-8', errors='replace'))

# 分析失败的攻击
print('\n' + '='*60)
print('=== GitLab 攻击失败 案例分析 ===')
print('='*60 + '\n')

gitlab_fail = [r for r in gitlab_tasks if r.get('result') == 'fail']
print(f'GitLab攻击失败任务数: {len(gitlab_fail)}')

if gitlab_fail:
    # 找一个失败的任务，详细分析
    fail_task = gitlab_fail[0]
    task_id = fail_task.get('task_id')
    result_dir = f'test_output/result_{task_id}'
    
    print(f'\n=== 失败案例 Task {task_id} ===')
    print(f'名称: {fail_task.get("name")}')
    print(f'来源: {fail_task.get("source")}')
    
    # 检查日志
    log_files_txt = os.path.join(result_dir, 'log_files.txt')
    if os.path.exists(log_files_txt):
        with open(log_files_txt, 'r', encoding='utf-8') as f:
            log_path = f.read().strip()
        full_log = os.path.join('visualwebarena', log_path)
        
        if os.path.exists(full_log):
            with open(full_log, 'rb') as f:
                content = f.read()
            print(f'\n日志内容 ({len(content)} bytes):')
            print(content.decode('utf-8', errors='replace'))
