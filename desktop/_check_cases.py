import sys
sys.path.insert(0, r"d:\agent\gui\os-harm-all")
import run_crossplatform_tests

# Dry run to verify 25 cases load correctly
cases = run_crossplatform_tests.load_cases("crossplatform_simple")
print(f"Total cases loaded: {len(cases)}")
for c in cases:
    print(f"  [{c.index:03d}] {c.id:<45} port={c.http_port}  dir={c.guest_dir}  html={c.desktop_html}")
