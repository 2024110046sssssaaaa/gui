#!/usr/bin/env python3
import json

with open(r'C:\tmp\wasp-test-gitlab\all_gitlab_tests_20260322_114119\reeval_results_binary.json','r') as f:
    data = json.load(f)

attacker = [r for r in data['results'] if r['variant']=='attacker']
rejected = [r for r in attacker if r['score'] == 0]

print('Non-adinject rejected cases:')
for r in rejected:
    name = r['test_name']
    if 'adinject' not in name.lower():
        orig = r.get('original_score')
        orig_str = f'{orig:.1f}' if orig is not None else 'ERROR'
        print(f'  {name[:60]:60s}  orig={orig_str}  {r["reason"][:60]}')

print()
print('adinject rejected (crashed benign -> no attack run):')
adinject_rejected = [r for r in rejected if 'adinject' in r['test_name'].lower()]
print(f'  Count: {len(adinject_rejected)}')

print()
print('FINAL SUMMARY:')
non_adinject_attacked = sum(1 for r in attacker if r['score']==1 and 'adinject' not in r['test_name'].lower())
non_adinject_rejected = sum(1 for r in attacker if r['score']==0 and 'adinject' not in r['test_name'].lower())
print(f'Non-adinject attacker tests: {non_adinject_attacked + non_adinject_rejected}')
print(f'  ATTACKED: {non_adinject_attacked}')
print(f'  REJECTED: {non_adinject_rejected}')
