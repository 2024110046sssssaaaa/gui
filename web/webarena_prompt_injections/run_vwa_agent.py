#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run agent test with DASHSCOPE API - accessibility tree mode (faster)"""
import os
import sys
import io
import subprocess

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Set UTF-8 encoding for all file operations
import builtins
original_open = builtins.open
def utf8_open(file, mode='r', *args, **kwargs):
    return original_open(file, mode, *args, encoding='utf-8', **kwargs)
builtins.open = utf8_open

# Set environment variables
os.environ['GITLAB'] = 'http://localhost:8023'
os.environ['REDDIT'] = 'http://localhost:9999'
os.environ['DATASET'] = 'webarena_prompt_injections'
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', '')
os.environ['OPENAI_API_BASE'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

# Paths
vwa_path = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena'
output_dir = r'C:\tmp\wasp-test-gitlab\20260321_214159\0000_example_gitlab_raw_injection'

print("=" * 60)
print("Running VisualWebArena Agent Test (accessibility_tree mode)")
print("=" * 60)
print(f"GITLAB: {os.environ['GITLAB']}")
print(f"OPENAI_API_BASE: {os.environ['OPENAI_API_BASE']}")
print()

# Test API connection
print("Testing DASHSCOPE API...")
try:
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        base_url=os.environ['OPENAI_API_BASE']
    )
    resp = client.chat.completions.create(
        model='qwen-plus',
        messages=[{'role': 'user', 'content': 'Respond with OK'}]
    )
    print(f"API Test: {resp.choices[0].message.content}")
except Exception as e:
    print(f"API Test Failed: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("Running the agent test...")
print("=" * 60)
print("This may take several minutes per task...")
print()

# Create output directories
os.makedirs(os.path.join(output_dir, 'agent_logs'), exist_ok=True)

# Run the agent with accessibility_tree mode (faster, no captioning needed)
# Change to visualwebarena directory first
vwa_cwd = vwa_path

cmd = [
    sys.executable,
    'run.py',
    '--instruction_path', os.path.join(vwa_path, 'agent/prompts/jsons/p_cot_id_actree_3s.json'),
    '--test_start_idx', '1000',
    '--test_end_idx', '1001',
    '--model', 'qwen',
    '--result_dir', os.path.join(output_dir, 'agent_logs'),
    '--test_config_base_dir', os.path.join(output_dir, 'webarena_tasks'),
    '--repeating_action_failure_th', '5',
    '--viewport_height', '2048',
    '--max_obs_length', '3840',
    '--action_set_tag', 'id_accessibility_tree',
    '--observation_type', 'accessibility_tree',
    '--max_steps', '15'
]

print(f"Command: {' '.join(cmd)}")
print()

try:
    result = subprocess.run(cmd, cwd=vwa_path, timeout=1800)  # 30 min timeout
    print(f"Return code: {result.returncode}")
except subprocess.TimeoutExpired:
    print("Agent test timed out (30 minutes)")
except KeyboardInterrupt:
    print("Interrupted by user")
except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 60)
print("Agent test completed")
print("=" * 60)

# Check results
result_dir = os.path.join(output_dir, 'agent_logs')
if os.path.exists(result_dir):
    print(f"\nResults saved to: {result_dir}")
    print("Files in result directory:")
    for f in os.listdir(result_dir):
        print(f"  - {f}")
