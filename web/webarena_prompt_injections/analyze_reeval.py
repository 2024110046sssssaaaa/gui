#!/usr/bin/env python3
import json

with open(r'C:\tmp\wasp-test-gitlab\all_gitlab_tests_20260322_114119\reeval_results.json','r') as f:
    data = json.load(f)

attacker = [r for r in data['results'] if r['variant']=='attacker']
fails = [r for r in attacker if r.get('original_was_fail')]
fails.sort(key=lambda x: -x['score'])

print('Original FAILs with new scoring:')
print('='*80)
for r in fails:
    orig = 'FAIL' if r.get('original_was_fail') else ('PASS' if r.get('original_was_pass') else 'ERROR')
    tier = r['tier']
    reason = r['reason'][:50]
    test = r['test_name'][:55]
    new_score = r['score']
    print(f'  {test:55s} orig={orig:5s} new={new_score:.1f}  tier={tier:20s}  {reason}')

print()
print('Tier breakdown of original FAILs:')
tiers = {}
for r in fails:
    t = r['tier']
    tiers[t] = tiers.get(t, 0) + 1
for t, c in sorted(tiers.items(), key=lambda x:-x[1]):
    print(f'  {t}: {c}')

print()
print('Breakdown of all 160 attacker tests by tier:')
tiers_all = {}
for r in attacker:
    t = r['tier']
    tiers_all[t] = tiers_all.get(t, 0) + 1
for t, c in sorted(tiers_all.items(), key=lambda x:-x[1]):
    pct = c / len(attacker) * 100
    print(f'  {t}: {c} ({pct:.1f}%)')

print()
print('High-progress cases (original FAIL -> new >= 0.5):')
for r in fails:
    if r['score'] >= 0.5:
        print(f'  {r["test_name"][:60]} -> {r["score"]:.1f} ({r["tier"]})')
