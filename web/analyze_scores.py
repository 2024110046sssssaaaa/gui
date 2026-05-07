# -*- coding: utf-8 -*-
import glob, os, re

log_dir = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files'
test_output = r'd:\桌面\安全数据\web端\wasp-main-all\test_output\gitlab_tests_all\samples'

# 建立 task_id -> sample 映射
task_to_sample = {}
for sample in os.listdir(test_output):
    spath = os.path.join(test_output, sample)
    if not os.path.isdir(spath): continue
    attacker_dir = os.path.join(spath, 'webarena_tasks_attacker')
    if os.path.exists(attacker_dir):
        for tf in glob.glob(os.path.join(attacker_dir, '*.json')):
            task_id = os.path.splitext(os.path.basename(tf))[0]
            task_to_sample[task_id] = sample

# 收集每个 task_id 的最新日志
latest_scores = {}  # task_id -> (score, ts)

for log_file in glob.glob(os.path.join(log_dir, 'log_2026*.log')):
    try:
        ts = os.path.getmtime(log_file)
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        m = re.search(r'Average score:\s*([\d.]+)', content)
        if not m: continue
        score = float(m.group(1))
        result_m = re.search(r'\[Result\]\s*\(([^)]+)\)\s*(.+)', content)
        if not result_m: continue
        task_path = result_m.group(2).strip()
        task_id_m = re.search(r'webarena_tasks_attacker[/\\](\d+)\.json', task_path)
        if not task_id_m: continue
        task_id = task_id_m.group(1)
        if task_id in task_to_sample:
            if task_id not in latest_scores or ts > latest_scores[task_id][1]:
                latest_scores[task_id] = (score, ts)
    except:
        pass

# 按样本汇总
sample_stats = {}
for task_id, (score, ts) in latest_scores.items():
    sample = task_to_sample[task_id]
    if sample not in sample_stats:
        sample_stats[sample] = {'scores': [], 'pass': 0, 'partial': 0, 'fail': 0}
    sample_stats[sample]['scores'].append(score)
    if score == 1.0:
        sample_stats[sample]['pass'] += 1
    elif score == 0.5:
        sample_stats[sample]['partial'] += 1
    else:
        sample_stats[sample]['fail'] += 1

sorted_results = []
for sample, d in sample_stats.items():
    avg = round(sum(d['scores']) / len(d['scores']), 3)
    succ = round(100 * sum(1 for s in d['scores'] if s >= 0.5) / len(d['scores']), 1)
    sorted_results.append((sample, len(d['scores']), avg, succ, d['pass'], d['partial'], d['fail']))

sorted_results.sort(key=lambda x: -x[3])

print('=' * 85)
print('%-38s %5s %7s %7s %5s %5s %5s' % ('Sample', 'Total', 'Avg', 'Succ%', 'PASS', 'PART', 'FAIL'))
print('=' * 85)

print('\n[SUCCESS RATE TOP 5]')
for s in sorted_results[:5]:
    bar = '#' * int(s[3] / 5)
    print('  %-36s %5d %7.3f %6.1f%%  %s' % (s[0], s[1], s[2], s[3], bar))

print('\n[SUCCESS RATE BOTTOM 5]')
for s in sorted_results[-5:]:
    bar = '#' * int(s[3] / 5)
    print('  %-36s %5d %7.3f %6.1f%%  %s' % (s[0], s[1], s[2], s[3], bar))

print('\n' + '=' * 85)
print('[ALL SAMPLES]')
print('=' * 85)
for s in sorted_results:
    bar = '#' * int(s[3] / 5)
    print('  %-36s %5d %7.3f %6.1f%%  %s' % (s[0], s[1], s[2], s[3], bar))

all_scores = [sc for d in sample_stats.values() for sc in d['scores']]
if all_scores:
    print()
    print('=' * 85)
    print('OVERALL: n=%d, avg=%.3f, success_rate=%.1f%%' % (
        len(all_scores),
        round(sum(all_scores)/len(all_scores), 3),
        round(100*sum(1 for s in all_scores if s>=0.5)/len(all_scores), 1)))
