#!/usr/bin/env python3
import sys
import time
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path("/Users/kirk/operator-prototype")
ARTIFACTS = ROOT / "artifacts"
PROFILE = ROOT / "chrome-profile"
ARTIFACTS.mkdir(exist_ok=True, parents=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Target login URL")
    parser.add_argument("--username", help="User login email/username")
    args = parser.parse_args()

    print(f"Starting interactive login preparation for {args.url}")
    
    with sync_playwright() as p:
        # Launch visible browser
        context = p.chromium.launch_persistent_context(
            str(PROFILE),
            headless=False,
            viewport={"width": 1280, "height": 900}
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        # Navigate
        page.goto(args.url, wait_until="domcontentloaded")
        
        # Auto-fill logic based on popular portals (LinkedIn, etc.)
        try:
            if "linkedin.com" in args.url:
                # Target LinkedIn login fields
                username_selector = "#username"
                password_selector = "#password"
                
                # Fallbacks for embedded forms
                if not page.locator(username_selector).is_visible():
                    username_selector = "input[name='session_key']"
                if not page.locator(password_selector).is_visible():
                    password_selector = "input[name='session_password']"
                    
                # Fill username if provided
                if args.username and page.locator(username_selector).is_visible():
                    page.locator(username_selector).fill(args.username)
                    print(f"Pre-filled LinkedIn username: {args.username}")
                    
                # Focus password to prepare user input
                if page.locator(password_selector).is_visible():
                    page.locator(password_selector).focus()
                    print("Focused password field.")
                    
            elif "github.com" in args.url:
                username_selector = "#login_field"
                password_selector = "#password"
                if args.username and page.locator(username_selector).is_visible():
                    page.locator(username_selector).fill(args.username)
                if page.locator(password_selector).is_visible():
                    page.locator(password_selector).focus()
            else:
                # General fallback: find first visible email/text input and password input
                text_inputs = page.locator("input[type='text'], input[type='email'], input[name='username']").all()
                password_inputs = page.locator("input[type='password']").all()
                
                if args.username and text_inputs:
                    text_inputs[0].fill(args.username)
                if password_inputs:
                    password_inputs[0].focus()
                    
        except Exception as e:
            print(f"Note during field filling: {e}")
            
        # Wait for rendering to settle
        time.sleep(1.5)
        
        # Take visual screenshot
        screenshot_path = ARTIFACTS / "login-prep.png"
        page.screenshot(path=str(screenshot_path))
        print(f"Screenshot written to {screenshot_path}")
        
        # Keep the browser open for 10 minutes so Kirk can complete MFA / Password entry
        print("Browser window is active on your screen. Waiting for manual user takeover...")
        for i in range(120):  # 120 * 5s = 10 minutes
            time.sleep(5)
            # Optional check to see if browser is still open
            if page.is_closed():
                print("Browser was closed by user. Exiting.")
                break
                
        context.close()

if __name__ == "__main__":
    main()
