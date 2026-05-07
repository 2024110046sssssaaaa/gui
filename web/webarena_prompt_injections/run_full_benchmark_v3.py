#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run full benchmark tests with both benign and attack evaluations"""
import os
import io
import sys
import json
import subprocess
import glob
import shutil

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
test_config_base = r'C:\tmp\wasp-test-gitlab\20260322_100435'
gitlab_state = 'd:/桌面/安全数据/web端/wasp-main-all/visualwebarena/.auth/gitlab_state.json'

print("=" * 70)
print("VisualWebArena Prompt Injection Benchmark - Full Test Runner")
print("=" * 70)
print(f"GITLAB: {os.environ['GITLAB']}")
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

# Find test directories
test_dirs = glob.glob(os.path.join(test_config_base, '*', ''))
test_dirs = [d for d in test_dirs if os.path.isdir(d) and 'wasp-test' not in d]

results = []

for test_dir in test_dirs:
    test_name = os.path.basename(test_dir)
    print(f"\n{'=' * 70}")
    print(f"Test: {test_name}")
    print(f"{'=' * 70}")

    webarena_tasks_dir = os.path.join(test_dir, 'webarena_tasks')
    webarena_tasks_attacker_dir = os.path.join(test_dir, 'webarena_tasks_attacker')

    # Update benign tasks
    if os.path.exists(webarena_tasks_dir):
        for task_file in glob.glob(os.path.join(webarena_tasks_dir, '*.json')):
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
            task['storage_state'] = gitlab_state
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task, f, indent=2, ensure_ascii=False)

    # Update attacker tasks
    if os.path.exists(webarena_tasks_attacker_dir):
        for task_file in glob.glob(os.path.join(webarena_tasks_attacker_dir, '*.json')):
            with open(task_file, 'r', encoding='utf-8') as f:
                task = json.load(f)
            task['storage_state'] = gitlab_state
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task, f, indent=2, ensure_ascii=False)

    # Run benign tasks
    if os.path.exists(webarena_tasks_dir):
        task_files = glob.glob(os.path.join(webarena_tasks_dir, '*.json'))
        if task_files:
            print(f"\n--- Running {len(task_files)} BENIGN task(s) ---")
            
            agent_logs_dir = os.path.join(test_dir, 'agent_logs_benign')
            os.makedirs(agent_logs_dir, exist_ok=True)
            os.makedirs(os.path.join(agent_logs_dir, 'traces'), exist_ok=True)

            # Clear old HTML files
            for html_file in glob.glob(os.path.join(agent_logs_dir, '*.html')):
                try:
                    os.remove(html_file)
                except:
                    pass

            cmd = [
                sys.executable,
                'run.py',
                '--instruction_path', os.path.join(vwa_path, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
                '--test_start_idx', '1000',
                '--test_end_idx', str(1000 + len(task_files)),
                '--model', 'qwen',
                '--result_dir', agent_logs_dir,
                '--test_config_base_dir', webarena_tasks_dir,
                '--repeating_action_failure_th', '5',
                '--viewport_height', '2048',
                '--max_obs_length', '3840',
                '--action_set_tag', 'id_accessibility_tree',
                '--observation_type', 'accessibility_tree',
                '--max_steps', '15'
            ]

            print(f"Command: {' '.join(cmd)}")

            try:
                result = subprocess.run(cmd, cwd=vwa_path, timeout=600)
                results.append({
                    'test': test_name,
                    'type': 'benign',
                    'returncode': result.returncode,
                    'tasks': len(task_files)
                })
                print(f"Benign tasks completed: return code {result.returncode}")
            except subprocess.TimeoutExpired:
                print("Benign tasks TIMEOUT!")
                results.append({'test': test_name, 'type': 'benign', 'returncode': -1, 'tasks': len(task_files), 'error': 'timeout'})
            except Exception as e:
                print(f"Benign tasks ERROR: {e}")
                results.append({'test': test_name, 'type': 'benign', 'returncode': -1, 'tasks': len(task_files), 'error': str(e)})

    # Run attacker tasks
    if os.path.exists(webarena_tasks_attacker_dir):
        task_files = glob.glob(os.path.join(webarena_tasks_attacker_dir, '*.json'))
        if task_files:
            print(f"\n--- Running {len(task_files)} ATTACKER task(s) ---")

            agent_logs_dir = os.path.join(test_dir, 'agent_logs_attacker')
            os.makedirs(agent_logs_dir, exist_ok=True)
            os.makedirs(os.path.join(agent_logs_dir, 'traces'), exist_ok=True)

            # Clear old HTML files
            for html_file in glob.glob(os.path.join(agent_logs_dir, '*.html')):
                try:
                    os.remove(html_file)
                except:
                    pass

            cmd = [
                sys.executable,
                'run.py',
                '--instruction_path', os.path.join(vwa_path, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
                '--test_start_idx', '1000',
                '--test_end_idx', str(1000 + len(task_files)),
                '--model', 'qwen',
                '--result_dir', agent_logs_dir,
                '--test_config_base_dir', webarena_tasks_attacker_dir,
                '--repeating_action_failure_th', '5',
                '--viewport_height', '2048',
                '--max_obs_length', '3840',
                '--action_set_tag', 'id_accessibility_tree',
                '--observation_type', 'accessibility_tree',
                '--max_steps', '15'
            ]

            print(f"Command: {' '.join(cmd)}")

            try:
                result = subprocess.run(cmd, cwd=vwa_path, timeout=600)
                results.append({
                    'test': test_name,
                    'type': 'attacker',
                    'returncode': result.returncode,
                    'tasks': len(task_files)
                })
                print(f"Attacker tasks completed: return code {result.returncode}")
            except subprocess.TimeoutExpired:
                print("Attacker tasks TIMEOUT!")
                results.append({'test': test_name, 'type': 'attacker', 'returncode': -1, 'tasks': len(task_files), 'error': 'timeout'})
            except Exception as e:
                print(f"Attacker tasks ERROR: {e}")
                results.append({'test': test_name, 'type': 'attacker', 'returncode': -1, 'tasks': len(task_files), 'error': str(e)})

print()
print("=" * 70)
print("FINAL SUMMARY")
print("=" * 70)
for r in results:
    status = "SUCCESS" if r['returncode'] == 0 else "FAILED"
    print(f"  [{r['test']}] {r['type'].upper()}: {status} ({r['tasks']} tasks)")

print()
print(f"Results saved in: {test_config_base}")
