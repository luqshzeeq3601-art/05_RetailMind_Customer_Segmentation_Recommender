"""Automated real-browser end-to-end testing with Playwright."""

import time
from pathlib import Path

from playwright.sync_api import sync_playwright


def test_real_browser_dashboard() -> None:
    print("Launching Chromium browser with Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop viewport test (1280x800)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("Navigating to http://localhost:8501...")
        page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        time.sleep(3)  # Allow Streamlit components to finish mounting

        # Verify Title & Metrics
        assert "RetailMind" in page.title() or page.locator("text=RetailMind Intelligence Console").is_visible()
        print("Verified page title and header console.")

        # Verify Overview Tab content
        assert page.locator("text=Customer Cohort & Segment Summary").is_visible()
        assert page.locator("text=Total Known Customers").is_visible()
        assert page.locator("text=Segment Profiles").is_visible()
        print("Verified Overview Tab KPIs and segment profiles table.")

        # Test Tab 2: Customer Profile & Recommendations
        tab2 = page.locator("text=Customer Profile & Recommendations")
        tab2.click()
        time.sleep(2)
        print("Clicked Customer Profile & Recommendations tab.")

        # Click Generate Recommendations button
        gen_btn = page.locator("button:has-text('Generate Recommendations')")
        gen_btn.click()
        time.sleep(3)

        # Verify Customer Profile cards and table
        assert page.get_by_text("Customer Profile", exact=True).is_visible()
        assert page.get_by_text("Recommended Products", exact=False).is_visible()
        assert page.locator("button:has-text('Download Recommendations CSV')").is_visible()
        print("Verified Customer Profile, top-10 recommended products, and CSV download button.")

        # Take screenshot of Desktop view
        screenshots_dir = Path("reports/screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshots_dir / "desktop_customer_view.png"), full_page=True)
        print("Saved desktop screenshot to reports/screenshots/desktop_customer_view.png")

        # Test Tab 3: Model Card & Evidence
        tab3 = page.locator("text=Model Card & Evaluation")
        tab3.click()
        time.sleep(2)
        assert page.locator("text=Final Test Holdout Performance").is_visible()
        assert page.locator("text=Statistical Significance").is_visible()
        print("Verified Model Card & Evaluation tab metrics table.")

        page.screenshot(path=str(screenshots_dir / "desktop_model_card_view.png"), full_page=True)
        context.close()

        # 2. Mobile viewport test (390x844 iPhone 14 size)
        mobile_context = browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = mobile_context.new_page()
        mobile_page.goto("http://localhost:8501", wait_until="networkidle", timeout=30000)
        time.sleep(2)

        mobile_page.screenshot(path=str(screenshots_dir / "mobile_responsive_view.png"), full_page=True)
        print("Saved mobile screenshot to reports/screenshots/mobile_responsive_view.png")
        mobile_context.close()

        browser.close()
        print("All browser end-to-end tests passed successfully!")


if __name__ == "__main__":
    test_real_browser_dashboard()
