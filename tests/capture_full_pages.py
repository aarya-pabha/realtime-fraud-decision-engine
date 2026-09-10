from playwright.sync_api import sync_playwright

def capture():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={'width': 1440, 'height': 900})
        page.goto('http://localhost:3000')
        page.wait_for_load_state('networkidle')
        page.screenshot(path='reports/webapp_tests/full_01_dashboard.png', full_page=True)
        
        page.locator('aside nav button:has-text("3DS Simulator")').click()
        page.wait_for_timeout(600)
        page.screenshot(path='reports/webapp_tests/full_02_simulator.png', full_page=True)
        
        page.locator('aside nav button:has-text("Drift")').click()
        page.wait_for_timeout(600)
        page.screenshot(path='reports/webapp_tests/full_03_drift.png', full_page=True)
        
        b.close()
        print("Full page screenshots saved successfully!")

if __name__ == "__main__":
    capture()
