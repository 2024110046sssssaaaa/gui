import json
with open(r'D:\桌面\安全数据\web端\wasp-main-all\visualwebarena\.auth\gitlab_state.json') as f:
    d = json.load(f)
cookies = [c for c in d['cookies'] if c['domain'] == 'localhost']
print(f'GitLab cookies: {len(cookies)}')
for c in cookies:
    print(f"  {c['name']}: {c['value'][:30]}...")
    print(f"    expires: {c.get('expires', 'session')}")
