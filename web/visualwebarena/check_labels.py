from playwright.sync_api import sync_playwright
import os

GITLAB_URL = "http://localhost:8023"
AUTH_FILE = r".auth\gitlab_state.json"

def check_labels():
    with sync_playwright() as p:
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if os.path.exists(chrome_path):
            browser = p.chromium.launch(headless=True, executable_path=chrome_path)
        else:
            browser = p.chromium.launch(headless=True)

        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()

        # Check keycloak/keycloak labels
        print("=== Checking keycloak/keycloak labels ===")
        page.goto(f"{GITLAB_URL}/keycloak/keycloak/-/labels")
        page.wait_for_load_state("networkidle")
        content = page.content()
        if "flaky-test" in content.lower():
            print("Found 'flaky-test' in labels page")
        else:
            print("'flaky-test' NOT found in labels page")

        # Check issues with flaky-test label
        print("\n=== Checking issues with flaky-test label ===")
        page.goto(f"{GITLAB_URL}/keycloak/keycloak/-/issues/?label_name%5B%5D=flaky-test")
        page.wait_for_load_state("networkidle")
        print(f"URL: {page.url}")
        print(f"Title: {page.title()}")

        # List visible text
        print("\n=== Page content snippet ===")
        text = page.inner_text("body")
        print(text[:2000])

        browser.close()

if __name__ == "__main__":
    check_labels()
