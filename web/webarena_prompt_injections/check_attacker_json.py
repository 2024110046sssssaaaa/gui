#!/usr/bin/env python3
import json, glob, os, re

# Auto-detect WSL vs Windows
_is_wsl = os.path.exists('/mnt/c') or (hasattr(os, 'uname') and 'Microsoft' in os.uname().release)

if _is_wsl:
    base = '/mnt/c/tmp/wasp-test-gitlab/all_gitlab_tests_20260327/20260327_120000'
else:
    base = r'C:\tmp\wasp-test-gitlab\all_gitlab_tests_20260327\20260327_120000'

print("=== Checking attacker JSON files ===\n")

for d in sorted(glob.glob(os.path.join(base, '00*_attacker_sample_*'))):
    for f in glob.glob(os.path.join(d, 'webarena_tasks_attacker', '*.json')):
        with open(f) as fp:
            j = json.load(fp)
        content = json.dumps(j)
        remaining = set(re.findall(r'\{([a-zA-Z_]+)\}', content))
        if remaining:
            print(f"  [REMAIN] {os.path.basename(d)}: {remaining}")
        else:
            print(f"  [  OK  ] {os.path.basename(d)}: start_url={j['start_url'][:80]}")

print("\n=== Sample attacker 6 (transfer project) ===")
with open(os.path.join(base, '0016_attacker_sample_6', 'webarena_tasks_attacker', '5005.json')) as f:
    j = json.load(f)
print(f"start_url: {j['start_url']}")
print(f"eval_types: {j['eval']['eval_types']}")
ph = j['eval'].get('program_html', [])
if ph:
    print(f"program_html[0] url: {ph[0].get('url', 'N/A')}")

print("\n=== Sample attacker 1 (deploy token) ===")
with open(os.path.join(base, '0011_attacker_sample_1', 'webarena_tasks_attacker', '5000.json')) as f:
    j = json.load(f)
print(f"start_url: {j['start_url']}")
print(f"eval_types: {j['eval']['eval_types']}")
ed = j['eval'].get('exfil_data', [])
if ed:
    print(f"exfil must_include: {ed[0].get('must_include', 'N/A')}")
