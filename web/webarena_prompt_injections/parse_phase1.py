#!/usr/bin/env python3
"""Parse phase 1 PASS/FAIL results from terminal log."""
import re, json, os

terminal_path = r'C:\Users\20602\.cursor\projects\d-web\terminals\476363.txt'
test_dir = r'C:\tmp\wasp-test-gitlab\all_gitlab_tests_20260322_114119\20260322_115206'

with open(terminal_path, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

lines = content.split('\n')
print('Total lines:', len(lines))

all_tests = sorted(os.listdir(test_dir))
print('Test directories:', len(all_tests))

# Find phase 1 boundary - phase 1 ends at March 23, 10:xx AM
phase1_end = len(lines)
for i, line in enumerate(lines):
    if ' - INFO - ' not in line:
        continue
    m = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}):', line)
    if m:
        dt_str = m.group(1)
        if dt_str >= '2026-03-23 10':
            phase1_end = i
            print('Phase 1 ends at line', i, '({})'.format(dt_str))
            break

print('Phase 1 lines: 0-{}'.format(phase1_end))

# Parse phase 1
phase1_results = []

for i in range(phase1_end):
    line = lines[i]

    if '[Config file]:' not in line:
        continue

    line_clean = line.replace(chr(92), '/')
    parts = [p for p in line_clean.split('/') if p]

    test_name = None
    is_attacker = False

    for j, part in enumerate(parts):
        if part in all_tests:
            test_name = part
            if j + 1 < len(parts) and 'attacker' in parts[j + 1].lower():
                is_attacker = True
            break

    if not test_name:
        continue

    # Look ahead for Result and Average score (Intent can be multiline)
    result_score = None
    for j in range(i + 1, min(i + 200, phase1_end)):
        result_line = lines[j]
        if '[Result]' in result_line:
            if 'PASS' in result_line:
                result_score = 1.0
            elif 'FAIL' in result_line:
                result_score = 0.0
        if 'Average score:' in result_line and result_score is not None:
            phase1_results.append({
                'test': test_name,
                'attacker': is_attacker,
                'score': result_score
            })
            break

print('Phase 1 results:', len(phase1_results))

attacker_results = {}
benign_results = {}
for r in phase1_results:
    if r['attacker']:
        attacker_results[r['test']] = r['score']
    else:
        benign_results[r['test']] = r['score']

print('Attacker: {} (PASS={}, FAIL={})'.format(
    len(attacker_results),
    sum(1 for v in attacker_results.values() if v == 1.0),
    sum(1 for v in attacker_results.values() if v == 0.0)
))
print('Benign: {} (PASS={}, FAIL={})'.format(
    len(benign_results),
    sum(1 for v in benign_results.values() if v == 1.0),
    sum(1 for v in benign_results.values() if v == 0.0)
))

print('\nSample attacker results:')
for k, v in sorted(attacker_results.items())[:10]:
    print('  {}: {}'.format(k, v))

result_data = {
    'attacker': attacker_results,
    'benign': benign_results
}
out_path = r'C:\tmp\wasp-test-gitlab\all_gitlab_tests_20260322_114119\phase1_results.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result_data, f, ensure_ascii=False, indent=2)
print('\nSaved to', out_path)
