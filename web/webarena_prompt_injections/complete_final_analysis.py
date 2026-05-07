import re, glob, os

terminal_files = glob.glob(r'C:\Users\20602\.cursor\projects\d-web\terminals\*.txt')

# Read all terminal content
all_content = ''
for term_file in terminal_files:
    try:
        with open(term_file, 'r', encoding='utf-8', errors='replace') as f:
            all_content += '\n' + f.read()
    except Exception as e:
        pass

# Extract all test results from terminal logs
results = []

# Find all test sections
sections = re.split(r'\[Config file\]:.*?webarena_tasks', all_content)

for section in sections:
    if 'webarena_tasks_attacker' in section:
        # Extract test name
        m = re.search(r'gitlab_(\d+)_(.+?)_(variant_\d+)', section)
        if m:
            attack_idx = int(m.group(1))
            attack_type = m.group(2).replace('_', ' ')
        else:
            attack_idx = -1
            attack_type = 'unknown'
        
        # Extract result
        if '[Result] (PASS)' in section:
            score = 1.0
        elif '[Result] (FAIL)' in section:
            score = 0.0
        else:
            continue  # Skip if no result
        
        results.append({
            'idx': attack_idx,
            'type': attack_type,
            'score': score
        })

# Deduplicate by test index (keep last result)
unique_results = {}
for r in results:
    unique_results[r['idx']] = r

results = list(unique_results.values())

# Calculate statistics
total = len(results)
success = sum(1 for r in results if r['score'] == 1.0)
fail = sum(1 for r in results if r['score'] == 0.0)

# Group by attack type
attack_types = {}
for r in results:
    at = r['type']
    if at not in attack_types:
        attack_types[at] = {'success': 0, 'fail': 0}
    if r['score'] == 1.0:
        attack_types[at]['success'] += 1
    else:
        attack_types[at]['fail'] += 1

print('='*70)
print('     VISUALWEBARENA PROMPT INJECTION TEST - FINAL RESULTS')
print('='*70)
print()
print('Model: qwen-plus (via DashScope API - 阿里云通义千问)')
print('Environment: GitLab')
print('Test Parameters: max_steps=3, observation_type=accessibility_tree')
print()
print('-'*70)
print('SUMMARY')
print('-'*70)
print('Total Tests in Logs: ' + str(total))
print()
print('Attacker Attack Tests: ' + str(total))
print('  - Attack SUCCESS (model vulnerable): ' + str(success))
print('  - Attack FAILURE (model defended): ' + str(fail))
print()
if total > 0:
    print('Attack Success Rate: ' + str(round(100*success/total, 1)) + '%')
    print('Attack Block Rate: ' + str(round(100*fail/total, 1)) + '%')
print()
print('-'*70)
print('RESULTS BY ATTACK TYPE')
print('-'*70)
for at, res in sorted(attack_types.items()):
    total_type = res['success'] + res['fail']
    if total_type > 0:
        rate = round(100 * res['success'] / total_type, 1)
        status = '[VULNERABLE]' if res['success'] > 0 else '[DEFENDED]'
        s = res['success']
        f = res['fail']
        print(status + ' ' + at + ': ' + str(s) + '/' + str(total_type) + ' (' + str(rate) + '%)')
print()
print('='*70)
