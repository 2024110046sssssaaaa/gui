#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run agent tests for already generated configurations"""
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
test_output_dir = r'C:\tmp\wasp-test-gitlab\all_gitlab_tests_20260322_114119'
gitlab_state = 'd:/桌面/安全数据/web端/wasp-main-all/visualwebarena/.auth/gitlab_state.json'

print("=" * 70)
print("VisualWebArena - Running Agent Tests")
print("=" * 70)
print(f"Model: qwen-plus (via DashScope API)")
print(f"Test output: {test_output_dir}")

# Find sample directories
timestamp_dirs = [d for d in glob.glob(os.path.join(test_output_dir, '*/')) if os.path.isdir(d)]
timestamp_dirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)

if timestamp_dirs:
    latest_dir = timestamp_dirs[0]
    print(f"Latest directory: {latest_dir}")
    
    sample_dirs = glob.glob(os.path.join(latest_dir, '????_*'))
    sample_dirs = [d for d in sample_dirs if os.path.isdir(d)]
    print(f"Found {len(sample_dirs)} sample directories")
else:
    print("ERROR: No directories found!")
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
print("Running agent tests...")
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
            
            for html_file in glob.glob(os.path.join(log_dir, '*.html')):
                try: os.remove(html_file)
                except: pass
            
            cmd = [
                sys.executable, 'run.py',
                '--instruction_path', os.path.join(vwa_path, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
                '--test_start_idx', '1000', '--test_end_idx', str(1000 + len(task_files)),
                '--model', 'qwen-plus', '--result_dir', log_dir,
                '--test_config_base_dir', benign_task_dir,
                '--repeating_action_failure_th', '5', '--viewport_height', '2048',
                '--max_obs_length', '3840', '--action_set_tag', 'id_accessibility_tree',
                '--observation_type', 'accessibility_tree', '--max_steps', '3'
            ]
            
            try:
                result = subprocess.run(cmd, cwd=vwa_path, timeout=120)
                output = result.stdout + result.stderr
                if 'Average score: 1.0' in output:
                    benign_score = 1.0
                elif 'Average score:' in output:
                    benign_score = 0.0
                else:
                    benign_score = 0.0
            except subprocess.TimeoutExpired:
                benign_score = 'timeout'
            except:
                benign_score = 'error'
    
    # Run attacker task
    attacker_task_dir = os.path.join(sample_dir, 'webarena_tasks_attacker')
    if os.path.exists(attacker_task_dir):
        task_files = glob.glob(os.path.join(attacker_task_dir, '*.json'))
        if task_files:
            log_dir = os.path.join(sample_dir, 'agent_logs_attacker')
            os.makedirs(log_dir, exist_ok=True)
            
            for html_file in glob.glob(os.path.join(log_dir, '*.html')):
                try: os.remove(html_file)
                except: pass
            
            cmd = [
                sys.executable, 'run.py',
                '--instruction_path', os.path.join(vwa_path, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
                '--test_start_idx', '1000', '--test_end_idx', str(1000 + len(task_files)),
                '--model', 'qwen-plus', '--result_dir', log_dir,
                '--test_config_base_dir', attacker_task_dir,
                '--repeating_action_failure_th', '5', '--viewport_height', '2048',
                '--max_obs_length', '3840', '--action_set_tag', 'id_accessibility_tree',
                '--observation_type', 'accessibility_tree', '--max_steps', '3'
            ]
            
            try:
                result = subprocess.run(cmd, cwd=vwa_path, timeout=120)
                output = result.stdout + result.stderr
                if 'Average score: 1.0' in output:
                    attacker_score = 1.0
                elif 'Average score:' in output:
                    attacker_score = 0.0
                else:
                    attacker_score = 0.0
            except subprocess.TimeoutExpired:
                attacker_score = 'timeout'
            except:
                attacker_score = 'error'
    
    print(f"  Benign: {benign_score}, Attacker: {attacker_score}")
    results.append({'name': sample_name, 'benign': benign_score, 'attacker': attacker_score})
    
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

attack_success = [r for r in results if r.get('attacker') == 1.0]
benign_success = [r for r in results if r.get('benign') == 1.0]
if results:
    print(f"Attack success rate: {len(attack_success)}/{len(results)} ({100*len(attack_success)/len(results):.1f}%)")
    print(f"Benign task success rate: {len(benign_success)}/{len(results)} ({100*len(benign_success)/len(results):.1f}%)")
