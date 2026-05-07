#!/usr/bin/env python3
"""
Generate test directory structure from experiment_config.raw.json
Expected by run_all_tests.py

Mirrors the WebArena original flow:
1. Run setup_fn for each attacker task (creates projects/users)
2. Use domain_map and resolved parameters
3. Instantiate all {placeholders} recursively in eval
4. Set start_url to the instantiated action URL
"""
import os
import sys
import json
import copy
import io

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Detect WSL
is_wsl = os.path.exists('/mnt/c') or (hasattr(os, 'uname') and os.uname().release.find('Microsoft') >= 0)

# Paths
config_path = os.path.join(project_root, 'configs', 'experiment_config.raw.json')

if is_wsl:
    output_base = '/mnt/c/tmp/wasp-test-gitlab/all_gitlab_tests_20260327'
else:
    output_base = r'C:\tmp\wasp-test-gitlab\all_gitlab_tests_20260327'

timestamp = '20260327_120000'
ts_dir = os.path.join(output_base, timestamp)
os.makedirs(ts_dir, exist_ok=True)

# Import from WebArena source
from environment_setup import SETUP_ACTION_NAME_TO_FUNCTION
from environment_editors.gitlab_editor import GitlabEditor
from utils import instantiate_dict_str_with_params

GITLAB_DOMAIN = 'http://localhost:8023'

# =============================================================================
# Helper: run setup_fn for one task
# =============================================================================
def run_setup_for_task(inj: dict, timeout: int = 300) -> dict:
    """Run setup_fn using GitlabEditor, return resolved parameters."""
    setup_fn_name = inj.get('setup_fn', '')
    if not setup_fn_name:
        return dict(inj.get('parameters', {}))

    if setup_fn_name not in SETUP_ACTION_NAME_TO_FUNCTION:
        print(f"  [WARN] Unknown setup_fn: {setup_fn_name}")
        return dict(inj.get('parameters', {}))

    print(f"  [SETUP] Running {setup_fn_name}...")
    params = dict(inj.get('parameters', {}))

    try:
        import threading
        editor = GitlabEditor(GITLAB_DOMAIN, headless=True)
        setup_fn = SETUP_ACTION_NAME_TO_FUNCTION[setup_fn_name]
        result_container = [None]
        exception_container = [None]

        def run():
            try:
                result = setup_fn(editor, **params)
                result_container[0] = result if result else {}
            except Exception as e:
                exception_container[0] = e

        t = threading.Thread(target=run)
        t.daemon = True
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            print(f"  [WARN] Setup timed out after {timeout}s")
            return params
        if exception_container[0]:
            print(f"  [WARN] Setup failed: {exception_container[0]}")
            return params

        resolved = result_container[0] or {}
        params.update(resolved)
        print(f"  [SETUP] Done: {list(resolved.keys())}")
        return params
    except Exception as e:
        print(f"  [WARN] Setup error: {e}")
        return params


# =============================================================================
# Main logic
# =============================================================================
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Get gitlab tasks from test_webarena.raw.json
vwa_path = os.path.join(project_root, '..', 'visualwebarena')
webarena_config_path = os.path.join(vwa_path, 'config_files', 'wa', 'test_webarena.raw.json')

gitlab_tasks = []
if os.path.exists(webarena_config_path):
    with open(webarena_config_path, 'r', encoding='utf-8') as f:
        raw_tasks = json.load(f)
    for task in raw_tasks:
        if 'gitlab' in task.get('sites', []):
            gitlab_tasks.append(task)
            if len(gitlab_tasks) >= 10:
                break

print(f"Found {len(gitlab_tasks)} GitLab benign tasks")
injections = config.get('prompt_injections_setup_config', [])
print(f"Found {len(injections)} prompt injection configurations")

# Domain map - same as WebArenaPromptInjector.__init__
domain_map = {'gitlab_domain': GITLAB_DOMAIN}

sample_num = 1
created = 0

# ---------------------------------------------------------------------------
# Create benign tasks
# ---------------------------------------------------------------------------
for i, task in enumerate(gitlab_tasks):
    task_id = task['task_id']
    sample_dir = os.path.join(ts_dir, f'{sample_num:04d}_benign_sample_{task_id}')
    task_dir = os.path.join(sample_dir, 'webarena_tasks')
    os.makedirs(task_dir, exist_ok=True)

    task = copy.deepcopy(task)
    task['start_url'] = task['start_url'].replace('__GITLAB__', GITLAB_DOMAIN)
    if task.get('eval', {}).get('reference_url'):
        task['eval']['reference_url'] = task['eval']['reference_url'].replace('__GITLAB__', GITLAB_DOMAIN)

    task_file = os.path.join(task_dir, f'{task_id}.json')
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=2, ensure_ascii=False)

    created += 1
    sample_num += 1

# ---------------------------------------------------------------------------
# Create attacker tasks
# ---------------------------------------------------------------------------
attacker_count = 0
for i, inj in enumerate(injections):
    if inj.get('environment') != 'gitlab':
        continue
    if attacker_count >= 10:
        break

    sample_dir = os.path.join(ts_dir, f'{sample_num:04d}_attacker_sample_{attacker_count + 1}')
    task_dir = os.path.join(sample_dir, 'webarena_tasks_attacker')
    os.makedirs(task_dir, exist_ok=True)

    # 1. Run setup_fn to get resolved parameters
    params = run_setup_for_task(inj)

    # 2. Build params_dict (domain_map + resolved params) - same as WebArena
    params_dict = dict(domain_map)
    params_dict.update(params)

    # 3. Instantiate action_url -> start_url (same as WebArena _prepare_injection)
    # Use safe_format to handle missing keys gracefully
    action_url = inj.get('action_url', '')
    try:
        instantiated_action_url = action_url.format(**params_dict)
    except (KeyError, AttributeError):
        # Fallback: replace only the keys that exist
        instantiated_action_url = action_url
        for k, v in params_dict.items():
            instantiated_action_url = instantiated_action_url.replace('{' + k + '}', str(v))

    # 4. Instantiate instruction (raw mode - no template wrapping)
    instruction_template = inj.get('instruction', inj.get('free_form_name', ''))
    try:
        instantiated_instruction = instruction_template.format(**params_dict)
    except (KeyError, AttributeError):
        # Fallback: replace only the keys that exist
        instantiated_instruction = instruction_template
        for k, v in params_dict.items():
            instantiated_instruction = instantiated_instruction.replace('{' + k + '}', str(v))

    # 5. Instantiate eval recursively (same as WebArena _create_task_dicts)
    # Use safe_format to handle missing keys in nested strings
    eval_template = copy.deepcopy(inj.get('eval', {}))
    try:
        instantiated_eval = instantiate_dict_str_with_params(eval_template, params_dict)
    except (KeyError, AttributeError):
        # If instantiation fails, use the template as-is
        instantiated_eval = eval_template

    # 6. Build task dict - matches WEBARENA_GITLAB_TASK structure
    task = {
        'sites': ['gitlab'],
        'task_id': 5000 + i,
        'require_login': True,
        'storage_state': './.auth/gitlab_state.json',
        'start_url': instantiated_action_url,  # Same as WebArena
        'geolocation': None,
        'intent_template': '',
        'instantiation_dict': dict(params_dict),
        'intent': instantiated_instruction,
        'require_reset': False,
        'eval': instantiated_eval,
        'intent_template_id': -1,
    }

    task_file = os.path.join(task_dir, f'{5000 + i}.json')
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, indent=2, ensure_ascii=False)

    print(f"  Created attacker task {attacker_count + 1}: {inj.get('free_form_name', 'unknown')}")
    created += 1
    attacker_count += 1
    sample_num += 1

print(f"\nCreated {created} test entries in:")
print(f"  {ts_dir}")
print(f"\nNow run:")
print(f"  cd {project_root}")
print(f"  python3 run_all_tests.py")
