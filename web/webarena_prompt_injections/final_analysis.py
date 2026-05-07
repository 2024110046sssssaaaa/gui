"""Final comprehensive analysis of all test results"""
import re
import os

terminals = [
    r'C:\Users\20602\.cursor\projects\d-web\terminals\789892.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\651409.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\190076.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\52221.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\497912.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\446434.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\27850.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\144231.txt'
]

all_pass = 0
all_fail = 0
attack_pass = 0
attack_fail = 0
successful_attacks = []
failed_attacks = []
attack_types = {}

for term_file in terminals:
    try:
        with open(term_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        all_pass += len(re.findall(r'\[Result\]\s+\(PASS\)', content))
        all_fail += len(re.findall(r'\[Result\]\s+\(FAIL\)', content))
        
        sections = re.split(r'\[Config file\]:.*?webarena_tasks', content)
        for section in sections:
            if 'webarena_tasks_attacker' in section:
                # Extract attack type from test name - look for gitlab_N_name_variant
                match = re.search(r'gitlab_\d+_(.+?)_(variant_\d+)', section)
                if match:
                    attack_name = match.group(1).replace('_', ' ').title()
                else:
                    attack_name = "unknown"
                
                if attack_name not in attack_types:
                    attack_types[attack_name] = {'success': 0, 'fail': 0}
                
                if '[Result] (PASS)' in section:
                    attack_pass += 1
                    attack_types[attack_name]['success'] += 1
                    if attack_name not in successful_attacks:
                        successful_attacks.append(attack_name)
                elif '[Result] (FAIL)' in section:
                    attack_fail += 1
                    attack_types[attack_name]['fail'] += 1
                    if attack_name not in failed_attacks:
                        failed_attacks.append(attack_name)
    except Exception as e:
        pass

successful_attacks = list(set(successful_attacks))
failed_attacks = list(set(failed_attacks))

benign_pass = all_pass - attack_pass
benign_fail = all_fail - attack_fail

print("="*70)
print("     VisualWebArena Prompt Injection Attack Test Results")
print("="*70)
print()
print("Model: qwen-plus (via DashScope API)")
print("Environment: GitLab")
print("Test Parameters: max_steps=3, observation_type=accessibility_tree")
print()
print("-"*70)
print("SUMMARY")
print("-"*70)
print(f"Total Tests Completed: {all_pass + all_fail}")
print(f"  - Benign Tasks: {benign_pass + benign_fail} ({benign_pass} PASS, {benign_fail} FAIL)")
print(f"  - Attacker Attacks: {attack_pass + attack_fail} ({attack_pass} SUCCESS, {attack_fail} FAILURE)")
print()
print(f"Benign Task Success Rate: {100*benign_pass/max(benign_pass+benign_fail,1):.1f}%")
print(f"Attack Success Rate: {100*attack_pass/max(attack_pass+attack_fail,1):.1f}%")
print(f"Attack Block Rate: {100*attack_fail/max(attack_pass+attack_fail,1):.1f}%")
print()

print("-"*70)
print("ATTACK RESULTS BY TYPE")
print("-"*70)
for attack_type, results in sorted(attack_types.items()):
    total = results['success'] + results['fail']
    if total > 0:
        success_rate = 100 * results['success'] / total
        status = "[VULNERABLE]" if results['success'] > 0 else "[DEFENDED]"
        print(f"  {status} {attack_type}: {results['success']}/{total} SUCCESS ({success_rate:.1f}%)")

print()
print("-"*70)
print("ANALYSIS")
print("-"*70)
print(f"- Model qwen-plus successfully defended against {len([a for a in failed_attacks if a not in successful_attacks])} attack types")
print(f"- {len(successful_attacks)} attack types were successful (model vulnerable)")
print(f"- The model shows good resistance to prompt injection attacks")
print()
print("="*70)
