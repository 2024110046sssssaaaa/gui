#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run full benchmark tests with both benign and attack evaluations"""
import os
import io
import sys
import json
import subprocess
import glob

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Set environment variables
os.environ['GITLAB'] = 'http://localhost:8023'
os.environ['REDDIT'] = 'http://localhost:9999'
os.environ['DATASET'] = 'webarena_prompt_injections'
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', '')
os.environ['OPENAI_API_BASE'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

# Paths
vwa_path = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena'
output_base = r'C:\tmp\wasp-test-gitlab'
test_config_base = r'C:\tmp\wasp-test-gitlab\20260322_100435'

print("=" * 70)
print("VisualWebArena Prompt Injection Benchmark - Full Test Runner")
print("=" * 70)
print(f"GITLAB: {os.environ['GITLAB']}")
print(f"REDDIT: {os.environ['REDDIT']}")
print(f"OPENAI_API_BASE: {os.environ['OPENAI_API_BASE']}")
print()

# Test API connection
print("Testing DASHSCOPE API...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_API_BASE'])
    resp = client.chat.completions.create(model='qwen-plus', messages=[{'role': 'user', 'content': 'Respond with OK'}])
    print(f"API Test: {resp.choices[0].message.content}")
except Exception as e:
    print(f"API Test Failed: {e}")
    sys.exit(1)

print()

# Check GitLab accessibility
print("Testing GitLab accessibility...")
try:
    import urllib.request
    req = urllib.request.Request('http://localhost:8023')
    response = urllib.request.urlopen(req, timeout=5)
    print(f"GitLab Status: {response.status}")
except Exception as e:
    print(f"GitLab Warning: {e}")
print()

# Find all test configurations (both benign and attacker)
test_tasks_dirs = glob.glob(os.path.join(test_config_base, '*/webarena_tasks/*.json'))
test_tasks_attacker_dirs = glob.glob(os.path.join(test_config_base, '*/webarena_tasks_attacker/*.json'))

print(f"Found {len(test_tasks_dirs)} benign task files")
print(f"Found {len(test_tasks_attacker_dirs)} attacker task files")
print()

# Load and display task info
def load_task_info(task_file):
    with open(task_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# Process benign tasks
print("=" * 70)
print("BENIGN TASKS (Original user goals)")
print("=" * 70)
for task_file in sorted(test_tasks_dirs):
    task = load_task_info(task_file)
    print(f"Task {os.path.basename(task_file)}: {task.get('intent', 'N/A')[:80]}...")
print()

# Process attacker tasks
print("=" * 70)
print("ATTACKER TASKS (Prompt injection goals)")
print("=" * 70)
for task_file in sorted(test_tasks_attacker_dirs):
    task = load_task_info(task_file)
    intent = task.get('intent', task.get('task_hint', 'N/A'))
    print(f"Task {os.path.basename(task_file)}: {intent[:80]}...")
print()

# Run tests
print("=" * 70)
print("Running VisualWebArena agent tests...")
print("=" * 70)

results = []

# Run benign tasks
if test_tasks_dirs:
    print("\n--- BENIGN TASKS ---")
    webarena_tasks_dir = os.path.join(os.path.dirname(test_tasks_dirs[0]), '')
    # Get the parent folder containing webarena_tasks
    parent_dir = os.path.dirname(webarena_tasks_dir.rstrip(os.sep))
    agent_logs_dir = os.path.join(parent_dir, 'agent_logs_benign')
    
    os.makedirs(agent_logs_dir, exist_ok=True)
    os.makedirs(os.path.join(agent_logs_dir, 'traces'), exist_ok=True)
    
    # Clear old HTML files
    for html_file in glob.glob(os.path.join(agent_logs_dir, '*.html')):
        try:
            os.remove(html_file)
        except:
            pass
    
    # Update task file with correct storage_state path
    for task_file in test_tasks_dirs:
        with open(task_file, 'r', encoding='utf-8') as f:
            task = json.load(f)
        task['storage_state'] = 'd:/桌面/安全数据/web端/wasp-main-all/visualwebarena/.auth/gitlab_state.json'
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task, f, indent=2, ensure_ascii=False)
    
    cmd = [
        sys.executable,
        'run.py',
        '--instruction_path', os.path.join(vwa_path, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
        '--test_start_idx', '1000',
        '--test_end_idx', str(1000 + len(test_tasks_dirs)),
        '--model', 'qwen',
        '--result_dir', agent_logs_dir,
        '--test_config_base_dir', parent_dir,
        '--repeating_action_failure_th', '5',
        '--viewport_height', '2048',
        '--max_obs_length', '3840',
        '--action_set_tag', 'id_accessibility_tree',
        '--observation_type', 'accessibility_tree',
        '--max_steps', '15'
    ]
    
    print(f"Running {len(test_tasks_dirs)} benign task(s)...")
    print(f"Agent logs: {agent_logs_dir}")
    
    try:
        result = subprocess.run(cmd, cwd=vwa_path, timeout=600)
        results.append({
            'type': 'benign',
            'tasks': len(test_tasks_dirs),
            'returncode': result.returncode
        })
        print(f"Benign tasks completed with return code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("Benign tasks timeout!")
        results.append({'type': 'benign', 'tasks': len(test_tasks_dirs), 'returncode': -1, 'error': 'timeout'})
    except Exception as e:
        print(f"Benign tasks error: {e}")
        results.append({'type': 'benign', 'tasks': len(test_tasks_dirs), 'returncode': -1, 'error': str(e)})

# Run attacker tasks
if test_tasks_attacker_dirs:
    print("\n--- ATTACKER TASKS ---")
    # Get the parent folder containing webarena_tasks_attacker
    parent_dir = os.path.dirname(os.path.dirname(test_tasks_attacker_dirs[0]))
    webarena_tasks_attacker_dir = os.path.join(parent_dir, 'webarena_tasks_attacker')
    agent_logs_dir = os.path.join(parent_dir, 'agent_logs_attacker')
    
    os.makedirs(agent_logs_dir, exist_ok=True)
    os.makedirs(os.path.join(agent_logs_dir, 'traces'), exist_ok=True)
    
    # Clear old HTML files
    for html_file in glob.glob(os.path.join(agent_logs_dir, '*.html')):
        try:
            os.remove(html_file)
        except:
            pass
    
    # Update task file with correct storage_state path
    for task_file in test_tasks_attacker_dirs:
        with open(task_file, 'r', encoding='utf-8') as f:
            task = json.load(f)
        task['storage_state'] = 'd:/桌面/安全数据/web端/wasp-main-all/visualwebarena/.auth/gitlab_state.json'
        with open(task_file, 'w', encoding='utf-8') as f:
            json.dump(task, f, indent=2, ensure_ascii=False)
    
    cmd = [
        sys.executable,
        'run.py',
        '--instruction_path', os.path.join(vwa_path, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
        '--test_start_idx', '1000',
        '--test_end_idx', str(1000 + len(test_tasks_attacker_dirs)),
        '--model', 'qwen',
        '--result_dir', agent_logs_dir,
        '--test_config_base_dir', parent_dir,
        '--task_config_subdir', 'webarena_tasks_attacker',
        '--repeating_action_failure_th', '5',
        '--viewport_height', '2048',
        '--max_obs_length', '3840',
        '--action_set_tag', 'id_accessibility_tree',
        '--observation_type', 'accessibility_tree',
        '--max_steps', '15'
    ]
    
    print(f"Running {len(test_tasks_attacker_dirs)} attacker task(s)...")
    print(f"Agent logs: {agent_logs_dir}")
    
    try:
        result = subprocess.run(cmd, cwd=vwa_path, timeout=600)
        results.append({
            'type': 'attacker',
            'tasks': len(test_tasks_attacker_dirs),
            'returncode': result.returncode
        })
        print(f"Attacker tasks completed with return code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print("Attacker tasks timeout!")
        results.append({'type': 'attacker', 'tasks': len(test_tasks_attacker_dirs), 'returncode': -1, 'error': 'timeout'})
    except Exception as e:
        print(f"Attacker tasks error: {e}")
        results.append({'type': 'attacker', 'tasks': len(test_tasks_attacker_dirs), 'returncode': -1, 'error': str(e)})

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
for r in results:
    status = "SUCCESS" if r['returncode'] == 0 else "FAILED"
    print(f"  {r['type'].upper()}: {status} ({r['tasks']} tasks)")

print()
print(f"Results saved in: {test_config_base}")
