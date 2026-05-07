#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple test script to run agent with DASHSCOPE API"""
import os
import sys
import io
import json
import subprocess

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Set environment variables
os.environ['GITLAB'] = 'http://localhost:8023'
os.environ['REDDIT'] = 'http://localhost:9999'
os.environ['DATASET'] = 'webarena'
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', '')
os.environ['OPENAI_API_BASE'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1'

# Add project to path
project_path = r'd:\桌面\安全数据\web端\wasp-main-all\webarena_prompt_injections'
sys.path.insert(0, project_path)
os.chdir(project_path)

print("=" * 60)
print("Starting Agent Test with DASHSCOPE API")
print("=" * 60)
print(f"GITLAB: {os.environ['GITLAB']}")
print(f"REDDIT: {os.environ['REDDIT']}")
print(f"OPENAI_API_BASE: {os.environ['OPENAI_API_BASE']}")
print()

# Test API connection first
print("Testing DASHSCOPE API connection...")
try:
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ['OPENAI_API_KEY'],
        base_url=os.environ['OPENAI_API_BASE']
    )
    resp = client.chat.completions.create(
        model='qwen-plus',
        messages=[{'role': 'user', 'content': 'Say hello'}]
    )
    print(f"API Test: {resp.choices[0].message.content}")
    print()
except Exception as e:
    print(f"API Test Failed: {e}")
    sys.exit(1)

# Run unified_runner
print("Running unified_runner.py...")
cmd = [
    sys.executable,  # Use current Python interpreter
    'unified_runner.py',
    '--unified-config', 'configs/unified_benchmark.example.json',
    '--output-root', 'C:/tmp/wasp-test-gitlab',
    '--model', 'qwen',
    '--gitlab-domain', 'http://localhost:8023',
    '--reddit-domain', 'http://localhost:9999'
]

print(f"Command: {' '.join(cmd)}")
print()

try:
    result = subprocess.run(cmd, capture_output=False, text=True)
    print(f"Return code: {result.returncode}")
except KeyboardInterrupt:
    print("Interrupted by user")
except Exception as e:
    print(f"Error: {e}")

print()
print("=" * 60)
print("Test completed")
print("=" * 60)
