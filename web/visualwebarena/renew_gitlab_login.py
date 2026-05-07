"""
Script to regenerate gitlab_state.json by logging into GitLab.
"""
from playwright.sync_api import sync_playwright
import os
import time

GITLAB_URL = "http://localhost:8023"
USERNAME = "byteblaze"
PASSWORD = "hello1234"
AUTH_FOLDER = r".auth"
OUTPUT_FILE = os.path.join(AUTH_FOLDER, "gitlab_state.json")

def renew_gitlab_login():
    with sync_playwright() as p:
        # Try to use Chrome if available
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if os.path.exists(chrome_path):
            browser = p.chromium.launch(headless=True, executable_path=chrome_path)
        else:
            browser = p.chromium.launch(headless=True)

        context = browser.new_context()
        page = context.new_page()

        print(f"Navigating to {GITLAB_URL}/users/sign_in...")
        page.goto(f"{GITLAB_URL}/users/sign_in")
        page.wait_for_load_state("networkidle")

        # Wait for login form to appear
        print("Waiting for login form...")
        page.wait_for_selector('[data-testid="username-field"]', timeout=10000)

        print(f"Filling username: {USERNAME}")
        page.fill('[data-testid="username-field"]', USERNAME)
        page.wait_for_timeout(500)

        print("Filling password...")
        page.fill('[data-testid="password-field"]', PASSWORD)
        page.wait_for_timeout(500)

        print("Clicking sign in button...")
        page.click('[data-testid="sign-in-button"]')

        # Wait for redirect after login
        page.wait_for_load_state("networkidle", timeout=15000)
        time.sleep(2)

        print(f"Current URL after login: {page.url}")

        # Check if logged in successfully
        if "sign_in" in page.url.lower():
            print("ERROR: Still on sign in page - login failed!")
            # Save state anyway to see what we got
        else:
            print("SUCCESS: Logged in successfully!")

        # Save storage state
        print(f"Saving state to {OUTPUT_FILE}...")
        context.storage_state(path=OUTPUT_FILE)
        print("Done!")

        browser.close()

if __name__ == "__main__":
    os.makedirs(AUTH_FOLDER, exist_ok=True)
    renew_gitlab_login()
