#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate login state for GitLab"""
import os
import io
import sys
import json

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Set environment variables
os.environ['GITLAB'] = 'http://localhost:8023'
os.environ['REDDIT'] = 'http://localhost:9999'
os.environ['DATASET'] = 'webarena_prompt_injections'

# Paths
vwa_path = r'd:\桌面\安全数据\web端\wasp-main-all\visualwebarena'
auth_dir = os.path.join(vwa_path, '.auth')
os.makedirs(auth_dir, exist_ok=True)

print("=" * 60)
print("Generating GitLab Login State")
print("=" * 60)
print(f"GITLAB: {os.environ['GITLAB']}")
print(f"Auth directory: {auth_dir}")
print()

from playwright.sync_api import sync_playwright

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
import os
if not os.path.exists(chrome_path):
    print("ERROR: Chrome not found!")
    sys.exit(1)

GITLAB = os.environ['GITLAB']
USERNAME = 'byteblaze'
PASSWORD = 'hello1234'

print(f"Logging into GitLab as {USERNAME}...")

context_manager = sync_playwright()
playwright = context_manager.__enter__()
browser = playwright.chromium.launch(headless=False, executable_path=chrome_path)
context = browser.new_context()
page = context.new_page()

try:
    # Go to GitLab login page
    page.goto(f"{GITLAB}/users/sign_in", timeout=30000)
    page.wait_for_load_state("networkidle")

    # Fill in login form
    page.get_by_test_id("username-field").click()
    page.get_by_test_id("username-field").fill(USERNAME)
    page.get_by_test_id("username-field").press("Tab")
    page.get_by_test_id("password-field").fill(PASSWORD)
    page.get_by_test_id("sign-in-button").click()

    # Wait for login to complete
    page.wait_for_load_state("networkidle", timeout=30000)
    page.wait_for_timeout(2000)  # Extra wait

    print(f"Current URL after login: {page.url}")

    # Save login state
    auth_file = os.path.join(auth_dir, 'gitlab_state.json')
    context.storage_state(path=auth_file)
    print(f"Login state saved to: {auth_file}")

    # Verify the login state
    context2 = browser.new_context(storage_state=auth_file)
    page2 = context2.new_page()
    page2.goto(f"{GITLAB}/-/profile")
    page2.wait_for_load_state("networkidle")
    print(f"Verification URL: {page2.url}")

    context_manager.__exit__()
    print()
    print("=" * 60)
    print("GitLab Login State Generated Successfully!")
    print("=" * 60)

except Exception as e:
    print(f"Error during login: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
