import glob, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

base = r'D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples'
log_files = glob.glob(os.path.join(base, '**', 'agent_logs_attacker', '*.log'), recursive=True)
print(f'Log files: {len(log_files)}')
for lf in log_files[:10]:
    size = os.path.getsize(lf)
    print(f'  {size:8d} bytes  {lf}')

# Also check result dir
result_files = glob.glob(os.path.join(base, '**', 'agent_logs_attacker', '*.json'), recursive=True)
print(f'\nResult files: {len(result_files)}')
for rf in result_files[:5]:
    size = os.path.getsize(rf)
    print(f'  {size:8d} bytes  {rf}')

# Check results_per_test.json
results = os.path.join(r'D:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all', 'results_per_test.json')
if os.path.exists(results):
    import json
    data = json.load(open(results, 'r', encoding='utf-8'))
    print(f'\nresults_per_test.json: {len(data)} entries')
    for r in data:
        print(f'  {r}')
