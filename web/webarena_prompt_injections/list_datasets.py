import glob, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = r'D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples'
datasets = sorted([d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))])
total = 0
for i, d in enumerate(datasets):
    attacker_dir = os.path.join(base, d, 'webarena_tasks_attacker')
    cnt = len(glob.glob(os.path.join(attacker_dir, '*.json'))) if os.path.exists(attacker_dir) else 0
    print(f'{i+1:2d}. {d}: {cnt} attacks')
    total += cnt
print(f'\nTotal: {total} attacks across {len(datasets)} datasets')
