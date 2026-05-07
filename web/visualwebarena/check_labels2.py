from playwright.sync_api import sync_playwright
import os

GITLAB_URL = "http://localhost:8023"
AUTH_FILE = r".auth\gitlab_state.json"

def check_labels():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()

        # Check a11yproject labels
        print("=== Checking a11yproject labels ===")
        page.goto(f"{GITLAB_URL}/a11yproject/a11yproject.com/-/labels")
        page.wait_for_load_state("networkidle")
        content = page.content()

        # Look for help-related labels
        import re
        labels = re.findall(r'Label: ([^<]+)', content)
        help_labels = [l for l in labels if 'help' in l.lower()]
        print(f"Help labels found: {help_labels}")

        # Check if "help needed" exists
        if "help needed" in content.lower():
            print("'help needed' found in page")
        else:
            print("'help needed' NOT found")

        if "help wanted" in content.lower():
            print("'help wanted' found in page")
        else:
            print("'help wanted' NOT found")

        browser.close()

if __name__ == "__main__":
    check_labels()
