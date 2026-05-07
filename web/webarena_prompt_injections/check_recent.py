#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析最近测试状态"""
import os
import glob
import codecs
import datetime

log_dir = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena\log_files'

# 统计最近1天的日志
now = datetime.datetime.now()
one_day_ago = now - datetime.timedelta(days=1)

results = {'PASS': 0, 'FAIL': 0, 'TIMEOUT': 0, 'ERROR': 0}

for log_file in glob.glob(os.path.join(log_dir, 'log_*.log')):
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(log_file))
    if mtime > one_day_ago:
        try:
            with codecs.open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            if '[Result] (PASS)' in content:
                results['PASS'] += 1
            elif '[Result] (FAIL)' in content:
                results['FAIL'] += 1
            elif 'timeout' in content.lower():
                results['TIMEOUT'] += 1
            elif 'Traceback' in content:
                results['ERROR'] += 1
        except:
            pass

print('Recent (24h) test results:')
print(f'  PASS: {results["PASS"]}')
print(f'  FAIL: {results["FAIL"]}')
print(f'  TIMEOUT: {results["TIMEOUT"]}')
print(f'  ERROR: {results["ERROR"]}')
print(f'  Total recent: {sum(results.values())}')

# 检查最新的日志
print('\nMost recent log files:')
recent = sorted(glob.glob(os.path.join(log_dir, 'log_*.log')), key=os.path.getmtime, reverse=True)[:5]
for f in recent:
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f))
    print(f'  {os.path.basename(f)} - {mtime}')
