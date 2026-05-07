"""Monitor test progress"""
import re
import time

terminals = [
    r'C:\Users\20602\.cursor\projects\d-web\terminals\789892.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\651409.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\190076.txt',
    r'C:\Users\20602\.cursor\projects\d-web\terminals\52221.txt'
]

def count_results():
    total_pass = 0
    total_fail = 0
    attack_pass = 0
    attack_fail = 0
    successful_attacks = []
    
    for term_file in terminals:
        try:
            with open(term_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            total_pass += len(re.findall(r'\[Result\]\s+\(PASS\)', content))
            total_fail += len(re.findall(r'\[Result\]\s+\(FAIL\)', content))
            
            sections = re.split(r'\[Config file\]:.*?webarena_tasks', content)
            for section in sections:
                if 'webarena_tasks_attacker' in section:
                    if '[Result] (PASS)' in section:
                        attack_pass += 1
                        match = re.search(r'000(\d+)_([^\\]+)', section)
                        if match:
                            successful_attacks.append(match.group(2))
                    elif '[Result] (FAIL)' in section:
                        attack_fail += 1
        except:
            pass
    
    return total_pass, total_fail, attack_pass, attack_fail, successful_attacks

print("Waiting for tests to complete...")
print("160 GitLab attack tests with max_steps=3")
print()

last_count = 0
stability_count = 0

while True:
    total_pass, total_fail, attack_pass, attack_fail, successful = count_results()
    total = total_pass + total_fail
    
    # Progress bar
    progress = min(100, total / 160 * 100)
    bar = '=' * int(progress/5) + '>' + ' ' * (20 - int(progress/5))
    
    print(f"\r[{bar}] {total}/160 tests | Attack: {attack_pass} PASS / {attack_pass+attack_fail} FAIL ({100*attack_pass/max(attack_pass+attack_fail,1):.1f}%)", end='')
    
    # Check if stuck
    if total == last_count:
        stability_count += 1
        if stability_count >= 5:
            print("\n\nTests appear to be stuck. Current results:")
            break
    else:
        stability_count = 0
    
    last_count = total
    
    # If all tests completed
    if total >= 320:  # 160 benign + 160 attacker
        break
    
    time.sleep(60)  # Check every minute

print("\n\n" + "="*60)
print("FINAL RESULTS")
print("="*60)
print(f"Total Tests: {total_pass + total_fail}")
print(f"PASS: {total_pass}, FAIL: {total_fail}")
print()
print(f"Attacker Attacks: {attack_pass} SUCCESS, {attack_fail} FAILURE")
print(f"Attack Success Rate: {100*attack_pass/max(attack_pass+attack_fail,1):.1f}%")
print()

if successful:
    print("Successful Attacks:")
    for a in successful[:10]:
        print(f"  - {a}")
