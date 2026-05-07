from playwright.sync_api import sync_playwright
import json

# Load storage state
with open(r'.auth\gitlab_state.json') as f:
    storage_state = json.load(f)

import os
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
with sync_playwright() as p:
    if os.path.exists(chrome_path):
        browser = p.chromium.launch(headless=True, executable_path=chrome_path)
    else:
        browser = p.chromium.launch(headless=True)
    context = browser.new_context(storage_state=".auth\\gitlab_state.json")
    page = context.new_page()

    # Go to GitLab
    page.goto("http://localhost:8023")
    page.wait_for_load_state("networkidle")

    print(f"Current URL: {page.url}")

    # Check if logged in
    if "sign_in" in page.url.lower():
        print("NOT LOGGED IN - Redirected to login page")
    else:
        print("LOGGED IN - On dashboard or other page")

    # Try to go to todos page
    page.goto("http://localhost:8023/dashboard/todos")
    page.wait_for_load_state("networkidle")
    print(f"Todos page URL: {page.url}")

    browser.close()
