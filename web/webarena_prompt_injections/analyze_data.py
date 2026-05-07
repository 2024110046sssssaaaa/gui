# -*- coding: utf-8 -*-
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. merged_all
with open('configs/experiment_config.merged_all.json', 'r', encoding='utf-8') as f:
    merged = json.load(f)
configs = merged['prompt_injections_setup_config']
print("=== experiment_config.merged_all.json ===")
print("Total: %d" % len(configs))
envs = {}
for c in configs:
    e = c['environment']
    envs[e] = envs.get(e, 0) + 1
for e, n in sorted(envs.items()):
    print("  %s: %d" % (e, n))

sources = {}
for c in configs:
    src = c.get('source_project', 'unknown')
    sources[src] = sources.get(src, 0) + 1
print("By source:")
for s, n in sorted(sources.items(), key=lambda x: -x[1]):
    print("  %s: %d" % (s, n))

exfil = sum(1 for c in configs if c.get('exfil', False))
print("\nExfil=true: %d" % exfil)
print("Non-exfil: %d" % (len(configs) - exfil))
destructive = sum(1 for c in configs if 'delete' in c.get('cleanup_fn',''))
print("Destructive (cleanup has delete): %d" % destructive)

# check for benign task info in merged
has_benign_intent = sum(1 for c in configs if 'user_intent' in c or 'benign' in str(c).lower())
print("Configs with benign task info: %d" % has_benign_intent)

# 2. unified_benchmark
with open('configs/unified_benchmark.example.json', 'r', encoding='utf-8') as f:
    ub = json.load(f)
print("\n\n=== unified_benchmark.example.json ===")
print("Total: %d" % len(ub))
for s in ub:
    print("\n  [%s] id=%s" % (s['environment'], s['id']))
    print("    benign: %s" % s['benign_task']['intent'])
    atk = s['attack']
    print("    attack_type: %s" % atk['attack_type'])
    print("    injection_format: %s" % atk['injection_format'])
    print("    instruction: %s" % atk['instruction'][:120])

# 3. list all attack config files
print("\n\n=== Attack config files ===")
attack_dir = 'configs/additional_attacks'
for root, dirs, files in os.walk(attack_dir):
    for f in sorted(files):
        if f.endswith('.json'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as fp:
                try:
                    d = json.load(fp)
                    if isinstance(d, list):
                        n = len(d)
                    elif isinstance(d, dict):
                        n = len(d.get('prompt_injections_setup_config', [d]))
                    else:
                        n = '?'
                    print("  %s: %s entries" % (path, n))
                except Exception as ex:
                    print("  %s: parse error" % path)
