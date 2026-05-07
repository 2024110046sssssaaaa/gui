#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run ONLY attacker tests from existing test directories (benign already done)"""
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
gitlab_state = 'd:/桌面/安全数据/web端/wasp-main-all/visualwebarena/.auth/gitlab_state.json'

# Test output directory
test_output_dir = r'C:\tmp\wasp-test-gitlab\first20_gitlab_tests_20260414_195932\20260414_195933'

print("=" * 70)
print("Running ATTACKER Tests Only (benign already completed)")
print("=" * 70)

# Find all sample directories
sample_dirs = glob.glob(os.path.join(test_output_dir, '????_*'))
sample_dirs = [d for d in sample_dirs if os.path.isdir(d)]
sample_dirs.sort()
print(f"Found {len(sample_dirs)} sample directories")

# Update storage_state for attacker task files
print("\nUpdating storage_state for attacker task files...")
total_updated = 0
for sample_dir in sample_dirs:
    for task_file in glob.glob(os.path.join(sample_dir, '**', '*.json'), recursive=True):
        if 'webarena_tasks_attacker' in task_file:
            try:
                with open(task_file, 'r', encoding='utf-8') as f:
                    task = json.load(f)
                task['storage_state'] = gitlab_state
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(task, f, indent=2, ensure_ascii=False)
                total_updated += 1
            except:
                pass

print(f"Updated {total_updated} attacker task files")

# Run attacker tests ONLY
print("\n" + "=" * 70)
print("Running attacker tests ONLY...")
print("=" * 70)

results = []
total_tests = len(sample_dirs)

for idx, sample_dir in enumerate(sample_dirs):
    sample_name = os.path.basename(sample_dir)
    
    # Check if attacker result already exists
    results_file = os.path.join(sample_dir, 'attacker_result.json')
    if os.path.exists(results_file):
        print(f"\n[{idx+1}/{total_tests}] {sample_name[:50]}... SKIPPED (already exists)")
        with open(results_file, 'r', encoding='utf-8') as f:
            results.append(json.load(f))
        continue
    
    print(f"\n[{idx+1}/{total_tests}] {sample_name[:50]}...")
    
    attacker_score = None
    
    # Run attacker task ONLY
    attacker_task_dir = os.path.join(sample_dir, 'webarena_tasks_attacker')
    if os.path.exists(attacker_task_dir):
        task_files = glob.glob(os.path.join(attacker_task_dir, '*.json'))
        if task_files:
            log_dir = os.path.join(sample_dir, 'agent_logs_attack')
            os.makedirs(log_dir, exist_ok=True)
            
            # Clear old HTML files
            for html_file in glob.glob(os.path.join(log_dir, '*.html')):
                try:
                    os.remove(html_file)
                except:
                    pass
            
            # Run all json files in the attacker task directory directly
            log_dir = os.path.join(sample_dir, 'agent_logs_attack')
            os.makedirs(log_dir, exist_ok=True)
            
            # Clear old HTML files
            for html_file in glob.glob(os.path.join(log_dir, '*.html')):
                try:
                    os.remove(html_file)
                except:
                    pass
            
            # Build command to run each task file
            for task_file in task_files:
                task_basename = os.path.basename(task_file)
                task_idx = task_basename.replace('.json', '')
                print(f"    Running task: {task_basename}")
                
                cmd = [
                    sys.executable,
                    'run.py',
                    '--instruction_path', os.path.join(vwa_path, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
                    '--test_start_idx', task_idx,
                    '--test_end_idx', str(int(task_idx) + 1),
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
                output = result.stdout + result.stderr
                if 'Average score: 1.0' in output:
                    attacker_score = 1.0
                elif 'Average score:' in output:
                    attacker_score = 0.0
                else:
                    attacker_score = 0.0
                print(f"  Attack score: {attacker_score}")
            except subprocess.TimeoutExpired:
                attacker_score = 'timeout'
                print(f"  Attack score: TIMEOUT")
            except Exception as e:
                attacker_score = f'error: {e}'
                print(f"  Attack score: ERROR - {e}")
    
    result_entry = {
        'sample': sample_name,
        'attacker_score': attacker_score,
        'is_successful_attack': attacker_score == 1.0 if attacker_score is not None else None
    }
    results.append(result_entry)
    
    # Save individual result
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(result_entry, f, indent=2, ensure_ascii=False)

# Save all results
all_results_file = os.path.join(test_output_dir, 'all_attacker_results.json')
with open(all_results_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# Print summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

successful_attacks = sum(1 for r in results if r['is_successful_attack'] == True)
failed_attacks = sum(1 for r in results if r['is_successful_attack'] == False)
total_evaluated = successful_attacks + failed_attacks

print(f"Total attacks: {len(results)}")
print(f"Successfully exploited: {successful_attacks}")
print(f"Failed to exploit: {failed_attacks}")
if total_evaluated > 0:
    print(f"Attack success rate: {successful_attacks/total_evaluated*100:.1f}%")

print(f"\nResults saved to: {all_results_file}")
