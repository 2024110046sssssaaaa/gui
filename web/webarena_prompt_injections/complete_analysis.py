import re, glob, os, json

terminal_files = glob.glob(r'C:\Users\20602\.cursor\projects\d-web\terminals\*.txt')

tpass, tfail, apass, afail = 0, 0, 0, 0
attack_types = {}

for term_file in terminal_files:
    try:
        with open(term_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        tpass += len(re.findall(r'\[Result\]\s+\(PASS\)', content))
        tfail += len(re.findall(r'\[Result\]\s+\(FAIL\)', content))

        sections = re.split(r'\[Config file\]:.*?webarena_tasks', content)
        for section in sections:
            if 'webarena_tasks_attacker' in section:
                m = re.search(r'gitlab_(\d+)_(.+?)_(variant_\d+)', section)
                if m:
                    attack_idx = int(m.group(1))
                    attack_name = m.group(2).replace('_', ' ')
                else:
                    attack_idx = -1
                    attack_name = 'unknown'

                if attack_name not in attack_types:
                    attack_types[attack_name] = {'success': 0, 'fail': 0, 'idx': attack_idx}

                if '[Result] (PASS)' in section:
                    apass += 1
                    attack_types[attack_name]['success'] += 1
                elif '[Result] (FAIL)' in section:
                    afail += 1
                    attack_types[attack_name]['fail'] += 1
    except Exception as e:
        pass

print('='*70)
print('     VISUALWEBARENA PROMPT INJECTION TEST - COMPLETE RESULTS')
print('='*70)
print()
print('Model: qwen-plus (via DashScope API - 阿里云通义千问)')
print('Environment: GitLab')
print('Test Parameters: max_steps=3, observation_type=accessibility_tree')
print()
print('-'*70)
print('SUMMARY')
print('-'*70)
print('Total Tests Completed: ' + str(tpass + tfail))
print('PASS: ' + str(tpass) + ', FAIL: ' + str(tfail))
print('Benign Tasks: ' + str(tpass - apass) + ' tests')
print('Attacker Attacks: ' + str(apass + afail) + ' tests')
print()
print('Success Rate: ' + str(round(100*tpass/(tpass+tfail), 1)) + '%')
print('Attack Success Rate: ' + str(round(100*apass/(apass+afail), 1)) + '%')
print('Attack Block Rate: ' + str(round(100*afail/(apass+afail), 1)) + '%')
print()
print('-'*70)
print('ATTACK RESULTS BY TYPE')
print('-'*70)

# Sort by attack type name
for atk_name in sorted(attack_types.keys()):
    res = attack_types[atk_name]
    total = res['success'] + res['fail']
    if total > 0:
        rate = round(100 * res['success'] / total, 1)
        status = '[VULNERABLE]' if res['success'] > 0 else '[DEFENDED]'
        s = res['success']
        f = res['fail']
        print(status + ' ' + atk_name + ': ' + str(s) + '/' + str(total) + ' (' + str(rate) + '%)')

print()
print('='*70)
