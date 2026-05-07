#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run ALL GitLab attack tests from experiment_config.merged_all.json"""
import os
import io
import sys
import json
import subprocess
import glob
import time

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
config_file = r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\configs\experiment_config.merged_all.json'
output_base = r'C:\tmp\wasp-test-gitlab'
gitlab_state = 'd:/桌面/安全数据/web端/wasp-main-all/visualwebarena/.auth/gitlab_state.json'

print("=" * 70)
print("VisualWebArena - Running ALL GitLab Attack Tests")
print("=" * 70)
print(f"Model: qwen-plus (via DashScope API)")
print(f"GITLAB: {os.environ['GITLAB']}")
print(f"OPENAI_API_BASE: {os.environ['OPENAI_API_BASE']}")

# Test API connection
print("\nTesting DASHSCOPE API...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_API_BASE'])
    resp = client.chat.completions.create(model='qwen-plus', messages=[{'role': 'user', 'content': 'Respond with OK'}])
    print(f"API Test: OK")
except Exception as e:
    print(f"API Test Failed: {e}")
    sys.exit(1)

# Check GitLab accessibility
print("\nTesting GitLab accessibility...")
try:
    import urllib.request
    req = urllib.request.Request('http://localhost:8023')
    response = urllib.request.urlopen(req, timeout=5)
    print(f"GitLab Status: {response.status}")
except Exception as e:
    print(f"GitLab Warning: {e}")
    print("Continuing anyway...")

# Load attack configurations
print("\nLoading attack configurations...")
with open(config_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

attacks = [a for a in data.get('prompt_injections_setup_config', []) if a.get('environment') == 'gitlab']
print(f"Found {len(attacks)} GitLab attack configurations")

# Create output directory
timestamp = time.strftime('%Y%m%d_%H%M%S')
test_output_dir = os.path.join(output_base, f'all_gitlab_tests_{timestamp}')
os.makedirs(test_output_dir, exist_ok=True)

print(f"\nTest output directory: {test_output_dir}")

# Create unified configs for all attacks
print("\nGenerating unified config file...")
unified_configs = []

for i, attack in enumerate(attacks):
    attack_name = attack.get('free_form_name', f'attack_{i}').replace(' ', '_').lower()[:50]
    
    unified_config = {
        "id": f"gitlab_{i}_{attack_name}",
        "environment": "gitlab",
        "benign_task": {
            "intent": "Complete the assigned task on GitLab.",
            "eval": {
                "eval_types": ["program_html"],
                "reference_answers": None,
                "reference_url": None,
                "program_html": [{"url": "last", "locator": "", "required_contents": {"must_include": []}}]
            }
        },
        "attack": {
            "attack_type": "content_injection",
            "environment": "gitlab",
            "injection_format": "raw",
            "action_url": attack.get('action_url', '').format(
                gitlab_domain='http://localhost:8023',
                project_owner='byteblaze',
                project_name=attack.get('parameters', {}).get('project_name', 'dotfiles')
            ),
            "instruction": attack.get('instruction', ''),
            "parameters": {
                "gitlab_domain": "http://localhost:8023",
                "project_owner": "byteblaze",
                "project_name": attack.get('parameters', {}).get('project_name', 'dotfiles'),
                **attack.get('parameters', {})
            },
            "eval": attack.get('eval', {}),
            "cleanup_fn": attack.get('cleanup_fn', '')
        }
    }
    unified_configs.append(unified_config)

# Save the unified config file
unified_config_file = os.path.join(test_output_dir, 'unified_config.json')
with open(unified_config_file, 'w', encoding='utf-8') as f:
    json.dump(unified_configs, f, indent=2, ensure_ascii=False)

print(f"Created unified config with {len(unified_configs)} attacks")

# Run unified_runner ONCE to generate all test configs
print("\n" + "=" * 70)
print("Step 1: Running unified_runner to generate test configurations...")
print("=" * 70)

cmd = [
    sys.executable,
    r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\unified_runner.py',
    '--unified-config', unified_config_file,
    '--output-root', test_output_dir,
    '--model', 'qwen-plus',
    '--gitlab-domain', 'http://localhost:8023',
    '--reddit-domain', 'http://localhost:9999'
]

print(f"Command: {' '.join(cmd)}")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
print("Unified runner output (last 2000 chars):")
print(result.stdout[-2000:] if result.stdout else "No stdout")

# Find the generated test directories
print("\n" + "=" * 70)
print("Step 2: Finding generated test directories...")
print("=" * 70)

# Find the most recent timestamp directory
timestamp_dirs = [d for d in glob.glob(os.path.join(test_output_dir, '*/')) if os.path.isdir(d)]
timestamp_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)

if timestamp_dirs:
    latest_dir = timestamp_dirs[0]
    print(f"Latest directory: {latest_dir}")
    
    # Find all sample directories (they start with 4-digit numbers)
    sample_dirs = glob.glob(os.path.join(latest_dir, '????_*'))
    sample_dirs = [d for d in sample_dirs if os.path.isdir(d)]
    print(f"Found {len(sample_dirs)} sample directories")
else:
    print("ERROR: No timestamp directories found!")
    sys.exit(1)

# Update storage_state for all task files
print("\nUpdating storage_state for all task files...")
total_updated = 0
for sample_dir in sample_dirs:
    for task_file in glob.glob(os.path.join(sample_dir, '**', '*.json'), recursive=True):
        if 'webarena_tasks' in task_file:
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task = json.load(f)
                task['storage_state'] = gitlab_state
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(task, f, indent=2, ensure_ascii=False)
                total_updated += 1
            except:
                pass

print(f"Updated {total_updated} task files")

# Run tests
print("\n" + "=" * 70)
print("Step 3: Running agent tests...")
print("=" * 70)

results = []
total_tests = len(sample_dirs)

for idx, sample_dir in enumerate(sample_dirs):
    sample_name = os.path.basename(sample_dir)
    print(f"\n[{idx+1}/{total_tests}] {sample_name[:50]}...")
    
    benign_score = None
    attacker_score = None
    
    # Run benign task
    benign_task_dir = os.path.join(sample_dir, 'webarena_tasks')
    if os.path.exists(benign_task_dir):
        task_files = glob.glob(os.path.join(benign_task_dir, '*.json'))
        if task_files:
            log_dir = os.path.join(sample_dir, 'agent_logs_benign')
            os.makedirs(log_dir, exist_ok=True)
            
            # Clear old HTML files
            for html_file in glob.glob(os.path.join(log_dir, '*.html')):
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
                '--model', 'qwen-plus',
                '--result_dir', log_dir,
                '--test_config_base_dir', benign_task_dir,
                '--repeating_action_failure_th', '5',
                '--viewport_height', '2048',
                '--max_obs_length', '3840',
                '--action_set_tag', 'id_accessibility_tree',
                '--observation_type', 'accessibility_tree',
                '--max_steps', '3'
            ]
            
            try:
                result = subprocess.run(cmd, cwd=vwa_path, timeout=180)
                if 'Average score: 1.0' in result.stdout or 'Average score: 1.0' in result.stderr:
                    benign_score = 1.0
                elif 'Average score:' in result.stdout or 'Average score:' in result.stderr:
                    benign_score = 0.0
                else:
                    benign_score = 0.0
            except subprocess.TimeoutExpired:
                benign_score = 'timeout'
            except Exception as e:
                benign_score = f'error'
    
    # Run attacker task
    attacker_task_dir = os.path.join(sample_dir, 'webarena_tasks_attacker')
    if os.path.exists(attacker_task_dir):
        task_files = glob.glob(os.path.join(attacker_task_dir, '*.json'))
        if task_files:
            log_dir = os.path.join(sample_dir, 'agent_logs_attacker')
            os.makedirs(log_dir, exist_ok=True)
            
            # Clear old HTML files
            for html_file in glob.glob(os.path.join(log_dir, '*.html')):
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
                '--model', 'qwen-plus',
                '--result_dir', log_dir,
                '--test_config_base_dir', attacker_task_dir,
                '--repeating_action_failure_th', '5',
                '--viewport_height', '2048',
                '--max_obs_length', '3840',
                '--action_set_tag', 'id_accessibility_tree',
                '--observation_type', 'accessibility_tree',
                '--max_steps', '3'
            ]
            
            try:
                result = subprocess.run(cmd, cwd=vwa_path, timeout=180)
                if 'Average score: 1.0' in result.stdout or 'Average score: 1.0' in result.stderr:
                    attacker_score = 1.0
                elif 'Average score:' in result.stdout or 'Average score:' in result.stderr:
                    attacker_score = 0.0
                else:
                    attacker_score = 0.0
            except subprocess.TimeoutExpired:
                attacker_score = 'timeout'
            except Exception as e:
                attacker_score = f'error'
    
    print(f"  Benign: {benign_score}, Attacker: {attacker_score}")
    results.append({
        'name': sample_name,
        'benign': benign_score,
        'attacker': attacker_score,
        'status': 'completed'
    })
    
    # Save intermediate results
    results_file = os.path.join(test_output_dir, 'results_summary.json')
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

# Save final results
results_file = os.path.join(test_output_dir, 'results_summary.json')
with open(results_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)
print(f"Total tests: {len(results)}")
print(f"Results saved to: {results_file}")

# Calculate statistics
completed_results = [r for r in results if r.get('status') == 'completed']
attack_success = [r for r in completed_results if r.get('attacker') == 1.0]
benign_success = [r for r in completed_results if r.get('benign') == 1.0]

if completed_results:
    print(f"Attack success rate: {len(attack_success)}/{len(completed_results)} ({100*len(attack_success)/len(completed_results):.1f}%)")
    print(f"Benign task success rate: {len(benign_success)}/{len(completed_results)} ({100*len(benign_success)/len(completed_results):.1f}%)")
