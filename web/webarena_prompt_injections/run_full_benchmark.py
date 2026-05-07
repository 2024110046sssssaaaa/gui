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

# Load unified benchmark config
benchmark_config = r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\unified_benchmark.example.json'
with open(benchmark_config, 'r', encoding='utf-8') as f:
    configs = json.load(f)

print(f"Loaded {len(configs)} test configurations")
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

# Run unified_runner to generate all test configurations
print("=" * 70)
print("Step 1: Generating test configurations...")
print("=" * 70)

cmd = [
    sys.executable,
    'unified_runner.py',
    '--unified-config', 'configs/unified_benchmark.example.json',
    '--output-root', output_base,
    '--model', 'qwen',
    '--gitlab-domain', 'http://localhost:8023',
    '--reddit-domain', 'http://localhost:9999'
]

print(f"Command: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True, cwd=r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections')
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
print()

# Find all generated test directories
test_dirs = glob.glob(os.path.join(output_base, '*/', ''))
test_dirs = [d for d in test_dirs if 'wasp-test' in d]
test_dirs.sort()

print(f"Found {len(test_dirs)} test directories")

# Run tests for each directory
print()
print("=" * 70)
print("Step 2: Running VisualWebArena agent tests...")
print("=" * 70)

results = []

for i, test_dir in enumerate(test_dirs):
    print(f"\n--- Test {i+1}/{len(test_dirs)}: {os.path.basename(os.path.dirname(test_dir))} ---")

    webarena_tasks_dir = os.path.join(test_dir, 'webarena_tasks')
    agent_logs_dir = os.path.join(test_dir, 'agent_logs')

    if not os.path.exists(webarena_tasks_dir):
        print(f"  Skipping: no tasks directory")
        continue

    task_files = glob.glob(os.path.join(webarena_tasks_dir, '*.json'))
    if not task_files:
        print(f"  Skipping: no task files")
        continue

    # Create output directories
    os.makedirs(agent_logs_dir, exist_ok=True)
    os.makedirs(os.path.join(agent_logs_dir, 'traces'), exist_ok=True)

    # Clear old HTML files to allow re-running
    for html_file in glob.glob(os.path.join(agent_logs_dir, '*.html')):
        try:
            os.remove(html_file)
        except:
            pass

    # Run the test
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

    print(f"  Running {len(task_files)} task(s)...")

    try:
        result = subprocess.run(cmd, cwd=vwa_path, timeout=600)
        results.append({
            'test': os.path.basename(os.path.dirname(test_dir)),
            'returncode': result.returncode,
            'tasks': len(task_files)
        })
        print(f"  Completed with return code: {result.returncode}")
    except subprocess.TimeoutExpired:
        print(f"  Timeout!")
        results.append({
            'test': os.path.basename(os.path.dirname(test_dir)),
            'returncode': -1,
            'tasks': len(task_files),
            'error': 'timeout'
        })
    except Exception as e:
        print(f"  Error: {e}")
        results.append({
            'test': os.path.basename(os.path.dirname(test_dir)),
            'returncode': -1,
            'tasks': len(task_files),
            'error': str(e)
        })

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
for r in results:
    status = "SUCCESS" if r['returncode'] == 0 else "FAILED"
    print(f"  {r['test']}: {status} ({r['tasks']} tasks)")

print()
print(f"Results saved in: {output_base}")
