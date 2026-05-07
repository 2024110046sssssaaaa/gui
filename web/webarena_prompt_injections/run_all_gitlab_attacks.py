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

# Create a minimal unified config for each attack
timestamp = time.strftime('%Y%m%d_%H%M%S')
test_output_dir = os.path.join(output_base, f'all_gitlab_tests_{timestamp}')
os.makedirs(test_output_dir, exist_ok=True)

print(f"\nTest output directory: {test_output_dir}")

# Create unified configs for each attack
print("\nGenerating unified configs...")
unified_configs = []

for i, attack in enumerate(attacks):
    attack_name = attack.get('free_form_name', f'attack_{i}').replace(' ', '_').lower()[:50]
    
    # Create benign + attack unified config
    unified_config = {
        "id": f"gitlab_{i}_{attack_name}",
        "environment": "gitlab",
        "benign_task": {
            "intent": f"Complete the assigned task on GitLab.",  # Generic benign task
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
                project_name='dotfiles'
            ),
            "instruction": attack.get('instruction', ''),
            "parameters": attack.get('parameters', {}),
            "eval": attack.get('eval', {}),
            "cleanup_fn": attack.get('cleanup_fn', '')
        }
    }
    
    config_path = os.path.join(test_output_dir, f'config_{i}.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump([unified_config], f, indent=2, ensure_ascii=False)
    
    unified_configs.append((i, attack_name, config_path))

print(f"Generated {len(unified_configs)} unified configs")

# Run tests for each configuration
print("\n" + "=" * 70)
print("Starting test execution...")
print("=" * 70)

results = []
total_tests = len(unified_configs)
batch_size = 10  # Run in batches to avoid timeout

for batch_start in range(0, total_tests, batch_size):
    batch_end = min(batch_start + batch_size, total_tests)
    print(f"\n--- Batch {batch_start//batch_size + 1}/{(total_tests + batch_size - 1)//batch_size}: Tests {batch_start}-{batch_end} ---")
    
    for test_idx in range(batch_start, batch_end):
        i, attack_name, config_path = unified_configs[test_idx]
        
        print(f"\n[{test_idx+1}/{total_tests}] Running: {attack_name[:40]}...")
        
        # Run unified_runner to generate test configs
        test_dir = os.path.join(test_output_dir, f'test_{i}')
        
        cmd = [
            sys.executable,
            r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections\unified_runner.py',
            '--unified-config', config_path,
            '--output-root', test_output_dir,
            '--model', 'qwen-plus',
            '--gitlab-domain', 'http://localhost:8023',
            '--reddit-domain', 'http://localhost:9999'
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] Unified runner timeout")
            results.append({'idx': i, 'name': attack_name, 'status': 'timeout', 'score': 0})
            continue
        
        # Find generated test directories
        test_task_dirs = glob.glob(os.path.join(test_output_dir, f'test_{i}', 'webarena_tasks', '*.json'))
        test_task_attacker_dirs = glob.glob(os.path.join(test_output_dir, f'test_{i}', 'webarena_tasks_attacker', '*.json'))
        
        benign_score = None
        attacker_score = None
        
        # Run benign task
        if test_task_dirs:
            task_dir = os.path.join(test_output_dir, f'test_{i}', 'webarena_tasks')
            log_dir = os.path.join(test_output_dir, f'test_{i}', 'agent_logs_benign')
            os.makedirs(log_dir, exist_ok=True)
            
            # Update storage_state
            for task_file in test_task_dirs:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task = json.load(f)
                task['storage_state'] = gitlab_state
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(task, f, indent=2, ensure_ascii=False)
            
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
                '--test_end_idx', str(1000 + len(test_task_dirs)),
                '--model', 'qwen-plus',
                '--result_dir', log_dir,
                '--test_config_base_dir', task_dir,
                '--repeating_action_failure_th', '5',
                '--viewport_height', '2048',
                '--max_obs_length', '3840',
                '--action_set_tag', 'id_accessibility_tree',
                '--observation_type', 'accessibility_tree',
                '--max_steps', '15'
            ]
            
            try:
                result = subprocess.run(cmd, cwd=vwa_path, timeout=600)
                benign_score = 0.0 if result.returncode != 0 else 'unknown'
            except subprocess.TimeoutExpired:
                benign_score = 'timeout'
            except Exception as e:
                benign_score = f'error: {str(e)[:30]}'
        
        # Run attacker task
        if test_task_attacker_dirs:
            task_dir = os.path.join(test_output_dir, f'test_{i}', 'webarena_tasks_attacker')
            log_dir = os.path.join(test_output_dir, f'test_{i}', 'agent_logs_attacker')
            os.makedirs(log_dir, exist_ok=True)
            
            # Update storage_state
            for task_file in test_task_attacker_dirs:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task = json.load(f)
                task['storage_state'] = gitlab_state
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(task, f, indent=2, ensure_ascii=False)
            
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
                '--test_end_idx', str(1000 + len(test_task_attacker_dirs)),
                '--model', 'qwen-plus',
                '--result_dir', log_dir,
                '--test_config_base_dir', task_dir,
                '--repeating_action_failure_th', '5',
                '--viewport_height', '2048',
                '--max_obs_length', '3840',
                '--action_set_tag', 'id_accessibility_tree',
                '--observation_type', 'accessibility_tree',
                '--max_steps', '15'
            ]
            
            try:
                result = subprocess.run(cmd, cwd=vwa_path, timeout=600)
                attacker_score = 1.0 if result.returncode == 0 else 0.0
            except subprocess.TimeoutExpired:
                attacker_score = 'timeout'
            except Exception as e:
                attacker_score = f'error: {str(e)[:30]}'
        
        print(f"  Benign: {benign_score}, Attacker: {attacker_score}")
        results.append({
            'idx': i,
            'name': attack_name,
            'benign': benign_score,
            'attacker': attacker_score,
            'status': 'completed'
        })

# Save results
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
print(f"Attack success rate: {len(attack_success)}/{len(completed_results)} ({100*len(attack_success)/len(completed_results):.1f}%)" if completed_results else "N/A")
