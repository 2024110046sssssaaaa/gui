# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

try:
    with open(r'C:\Users\20602\.cursor\projects\d-web\terminals\476363.txt', 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
except:
    with open(r'C:\Users\20602\.cursor\projects\d-web\terminals\476363.txt', 'r', errors='replace') as f:
        content = f.read()

lines = content.split('\n')

# Parse all [Result] lines
results = []
for l in lines:
    if '[Result]' in l and 'webarena_tasks' in l:
        m = re.search(r'webarena_tasks(?:_attacker)?\\1000\.json', l)
        if not m:
            m = re.search(r'webarena_tasks(?:_attacker)?/1000\.json', l)
        is_attacker = 'webarena_tasks_attacker' in l
        is_pass = 'PASS' in l
        is_fail = 'FAIL' in l
        results.append({'line': l[:120], 'attacker': is_attacker, 'pass': is_pass, 'fail': is_fail})

benign_pass = sum(1 for r in results if not r['attacker'] and r['pass'])
benign_fail = sum(1 for r in results if not r['attacker'] and r['fail'])
attacker_pass = sum(1 for r in results if r['attacker'] and r['pass'])
attacker_fail = sum(1 for r in results if r['attacker'] and r['fail'])
unknown = sum(1 for r in results if not r['pass'] and not r['fail'])

print("=== 476363.txt Result Analysis ===")
print("Benign PASS: %d" % benign_pass)
print("Benign FAIL: %d" % benign_fail)
print("Attacker PASS: %d" % attacker_pass)
print("Attacker FAIL: %d" % attacker_fail)
print("Unknown: %d" % unknown)
print("Total: %d" % len(results))
print()

# Count Config file lines too
configs = [l for l in lines if '[Config file]' in l and 'webarena_tasks' in l]
attacker_cfgs = [l for l in configs if 'webarena_tasks_attacker' in l]
benign_cfgs = [l for l in configs if 'webarena_tasks_attacker' not in l]
print("Benign Config lines: %d" % len(benign_cfgs))
print("Attacker Config lines: %d" % len(attacker_cfgs))

# Show which tests have no result
cfg_set = set()
for l in configs:
    m = re.search(r'20260322_115206[\\\\/]([^\\\\/]+)[\\\\/]webarena_tasks', l)
    if m:
        cfg_set.add(m.group(1))

result_set = set()
for l in lines:
    if '[Result]' in l and 'webarena_tasks' in l:
        m = re.search(r'20260322_115206[\\\\/]([^\\\\/]+)[\\\\/]webarena_tasks', l)
        if m:
            result_set.add(m.group(1))

no_result = sorted(cfg_set - result_set)
print("\nTests with Config but NO Result line (%d):" % len(no_result))
for t in no_result[:20]:
    print("  %s" % t)
