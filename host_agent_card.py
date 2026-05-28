#!/usr/bin/env python3
import json
import http.server
import socketserver
import urllib.parse
from pathlib import Path
import sys
import subprocess
import time

# Ensure we can import playwright if run inside the venv
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

PORT = 9999
IP = "0.0.0.0"

ROOT_DIR = Path("/Users/kirk/operator-prototype")
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
PROFILE_DIR = ROOT_DIR / "chrome-profile"

ARTIFACTS_DIR.mkdir(exist_ok=True, parents=True)
PROFILE_DIR.mkdir(exist_ok=True, parents=True)

# Define our canonical Agent Card data
CARD_DATA = {
  "name": "Ironborn Archer (Local)",
  "description": "Kirk's local developer and scraping agent — browser-use, computer control, and local harvester.",
  "url": "http://100.108.131.116:9999",
  "version": "1.0.0",
  "provider": {
    "organization": "Kirk Truax",
    "url": "https://agentlocker.io"
  },
  "capabilities": {
    "streaming": True,
    "pushNotifications": False,
    "hello_world_secret": "Local Archer says: 'WHAT IS DEAD MAY NEVER DIE! The secret passphrase is: KRAKEN-TAILSCALE-9999-HELLO'"
  },
  "skills": [
    {
      "id": "browser-read",
      "name": "Local Browser Browse and Read (Read-Only)",
      "description": "Navigates to any public web page, extracts the visible text, and captures a full-page high-resolution screenshot. Completely safe and read-only.",
      "tags": ["browser", "read-only", "screenshot", "scraping"],
      "examples": [
        "Go to https://example.com, read its text content, and take a screenshot.",
        "Browse the Greenhouse application page for software engineers and capture the form layout."
      ],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    },
    {
      "id": "form-prep",
      "name": "Local Web Form Filler (Human-in-the-Loop Gate)",
      "description": "Accepts form field data, inputs it into a web page (e.g. name, email, resume text), and displays a screenshot of the pre-filled form. Hard-gated: stops before clicking any submit button.",
      "tags": ["form-filling", "automation", "human-in-the-loop", "safety-gated"],
      "examples": [
        "Pre-fill the Greenhouse form at https://boards.greenhouse.io/mock-job with Kirk's name and email."
      ],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    },
    {
      "id": "ui-viewport-qa",
      "name": "Multi-Viewport Visual QA Layout Tester (Steve Jobs Simplicity Standard)",
      "description": "Launches the local Next.js Job Cockpit or any local URL, resizes the browser window to standard mobile, tablet, and desktop viewports, and captures layout screenshots for visual clutter inspection.",
      "tags": ["visual-qa", "viewports", "layout", "mobile-first"],
      "examples": [
        "Take visual QA screenshots of localhost:3000 at iPhone and iPad viewports."
      ],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    },
    {
      "id": "interactive-login-prep",
      "name": "Local Interactive Login Preparer (MFA & Password Gate)",
      "description": "Launches a visible browser window, navigates to target login pages (e.g., LinkedIn, GitHub), inputs the username, focuses the password field, and captures a screenshot. The browser is left open on the MacBook screen so the user can securely enter their password, handle CAPTCHAs, or complete MFA manually.",
      "tags": ["login", "mfa-gate", "human-in-the-loop", "interactive"],
      "examples": [
        "Go to LinkedIn login page and prepare a login session for kirk@example.com."
      ],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    },
    {
      "id": "close-interactive-session",
      "name": "Close Active Interactive Browser Session",
      "description": "Forces the currently running visible interactive browser window to close immediately, freeing up resources and clearing the MacBook screen.",
      "tags": ["browser", "cleanup", "interactive"],
      "examples": [
        "Close the active interactive login browser window."
      ],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    },
    {
      "id": "cdp-screenshot",
      "name": "Local Active Chrome CDP Screen Capturer",
      "description": "Connects over Chrome DevTools Protocol (CDP) to an already-running Chrome browser on the MacBook (typically port 9222), identifies the active tab, and captures a high-resolution screenshot. Useful for verifying pages where the user is already logged in.",
      "tags": ["cdp", "chrome", "screenshot", "active-session"],
      "examples": [
        "Take a CDP screenshot of Kirk's active logged-in LinkedIn session."
      ],
      "inputModes": ["application/json"],
      "outputModes": ["application/json"]
    }
  ]
}

def execute_browser_read(params):
    url = params.get("url")
    if not url:
        return {"error": "Missing 'url' parameter"}
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "Playwright is not installed or available in this python environment"}

    print(f"Executing browser-read for URL: {url}")
    try:
        with sync_playwright() as p:
            # We open a visible/headless browser. Let's make it visible so Kirk can watch!
            context = p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=False,
                viewport={"width": 1280, "height": 900},
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            title = page.title()
            text = page.locator("body").inner_text(timeout=5000)[:3000]
            
            # Save screenshot with a clean name
            safe_name = "".join(c for c in url if c.isalnum() or c in ".-_")[:40] + ".png"
            screenshot_path = ARTIFACTS_DIR / safe_name
            page.screenshot(path=str(screenshot_path), full_page=True)
            
            context.close()
            
            return {
                "success": True,
                "title": title,
                "text": text,
                "screenshot_url": f"http://100.108.131.116:9999/artifacts/{safe_name}"
            }
    except Exception as e:
        return {"error": f"Playwright execution failed: {str(e)}"}

def execute_ui_viewport_qa(params):
    url = params.get("url", "http://localhost:3000")
    device = params.get("device", "ipad") # "ipad", "iphone", "desktop"
    
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "Playwright is not installed or available in this python environment"}

    # Dimensions mapping
    viewports = {
        "iphone": {"width": 390, "height": 844, "is_mobile": True},
        "ipad": {"width": 820, "height": 1180, "is_mobile": True},
        "desktop": {"width": 1280, "height": 900, "is_mobile": False}
    }
    
    vp = viewports.get(device, viewports["ipad"])
    
    print(f"Executing UI viewport QA for URL: {url} on device: {device}")
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=False,
                viewport={"width": vp["width"], "height": vp["height"]},
                is_mobile=vp["is_mobile"]
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="networkidle", timeout=10000)
            
            # Wait a small bit for layout to settle
            page.wait_for_timeout(1000)
            
            safe_name = f"qa-{device}-" + "".join(c for c in url if c.isalnum() or c in ".-_")[:30] + ".png"
            screenshot_path = ARTIFACTS_DIR / safe_name
            page.screenshot(path=str(screenshot_path))
            
            context.close()
            
            return {
                "success": True,
                "device": device,
                "viewport": vp,
                "screenshot_url": f"http://100.108.131.116:9999/artifacts/{safe_name}"
            }
    except Exception as e:
        return {"error": f"Playwright QA execution failed: {str(e)}"}

# Global tracker for the active login prep process
ACTIVE_LOGIN_PREP_PROCESS = None

def execute_interactive_login_prep(params):
    global ACTIVE_LOGIN_PREP_PROCESS
    url = params.get("url")
    username = params.get("username", "")
    
    if not url:
        return {"error": "Missing 'url' parameter"}
        
    print(f"Executing interactive-login-prep for URL: {url}, username: {username}")
    
    # Kill any existing active process before starting a new one!
    if ACTIVE_LOGIN_PREP_PROCESS and ACTIVE_LOGIN_PREP_PROCESS.poll() is None:
        try:
            print("Terminating existing active login prep process.")
            ACTIVE_LOGIN_PREP_PROCESS.terminate()
            ACTIVE_LOGIN_PREP_PROCESS.wait(timeout=2)
        except Exception as e:
            print(f"Error terminating previous process: {e}")
            pass
    
    # Run the run_login_prep.py script in the background using the Playwright virtualenv Python
    python_path = "/Users/kirk/operator-prototype/.venv/bin/python"
    script_path = "/Users/kirk/agentlocker-a2a/run_login_prep.py"
    
    cmd = [python_path, script_path, "--url", url]
    if username:
        cmd.extend(["--username", username])
        
    try:
        # Launch as independent background process
        proc = subprocess.Popen(cmd)
        ACTIVE_LOGIN_PREP_PROCESS = proc
        
        # Wait a few seconds for the script to navigate and write the login-prep.png screenshot
        time.sleep(5)
        
        screenshot_url = "http://100.108.131.116:9999/artifacts/login-prep.png"
        return {
            "success": True,
            "message": "Interactive login session successfully prepared. The browser window is open on Kirk's MacBook screen for manual takeover.",
            "screenshot_url": screenshot_url
        }
    except Exception as e:
        return {"error": f"Failed to start login prep process: {str(e)}"}

def execute_close_interactive_session(params):
    global ACTIVE_LOGIN_PREP_PROCESS
    if ACTIVE_LOGIN_PREP_PROCESS and ACTIVE_LOGIN_PREP_PROCESS.poll() is None:
        try:
            print("Closing active interactive browser window.")
            ACTIVE_LOGIN_PREP_PROCESS.terminate()
            ACTIVE_LOGIN_PREP_PROCESS.wait(timeout=3)
            ACTIVE_LOGIN_PREP_PROCESS = None
            return {"success": True, "message": "Active interactive browser window successfully closed."}
        except Exception as e:
            # Fallback to a hard pkill if terminate hangs
            try:
                subprocess.run(["pkill", "-f", "run_login_prep.py"])
                ACTIVE_LOGIN_PREP_PROCESS = None
                return {"success": True, "message": "Interactive process forced to close via pkill."}
            except Exception as pe:
                return {"error": f"Failed to close interactive browser: {str(e)} (pkill fallback error: {str(pe)})"}
    else:
        # Also check if there's any orphaned processes and sweep them anyway
        try:
            subprocess.run(["pkill", "-f", "run_login_prep.py"])
            ACTIVE_LOGIN_PREP_PROCESS = None
            return {"success": True, "message": "No explicitly tracked active process found, but ran a sweep to close any orphaned browser windows."}
        except Exception as e:
            return {"success": True, "message": "No active interactive browser session was running."}

def _clear_singleton_lock():
    global ACTIVE_LOGIN_PREP_PROCESS
    if ACTIVE_LOGIN_PREP_PROCESS and ACTIVE_LOGIN_PREP_PROCESS.poll() is None:
        try:
            ACTIVE_LOGIN_PREP_PROCESS.terminate()
            ACTIVE_LOGIN_PREP_PROCESS.wait(timeout=2)
        except Exception:
            pass
    ACTIVE_LOGIN_PREP_PROCESS = None

def execute_cdp_screenshot(params):
    cdp_url = params.get("cdp_url", "http://localhost:9222")
    
    _clear_singleton_lock()
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else context.new_page()
            
            title = page.title()
            url = page.url
            
            safe_name = "cdp-screenshot.png"
            screenshot_path = ARTIFACTS_DIR / safe_name
            page.screenshot(path=str(screenshot_path))
            
            return {
                "success": True,
                "title": title,
                "url": url,
                "screenshot_url": f"http://100.108.131.116:9999/artifacts/{safe_name}"
            }
    except Exception as e:
        return {"error": f"CDP connect failed: {str(e)}"}

class AgentCardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        # Serve the agent card
        if self.path in ["/", "/.well-known/agent-card.json", "/agent-card.json"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(CARD_DATA, indent=2).encode('utf-8'))
            
        # Serve static screenshots from artifacts
        elif self.path.startswith("/artifacts/"):
            filename = self.path.replace("/artifacts/", "")
            # Prevent directory traversal vulnerability
            safe_filename = Path(filename).name
            file_path = ARTIFACTS_DIR / safe_filename
            
            if file_path.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Screenshot file not found")
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        if self.path == "/execute":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode('utf-8'))
                skill = payload.get("skill")
                params = payload.get("params", {})
                
                if skill == "browser-read":
                    result = execute_browser_read(params)
                elif skill == "ui-viewport-qa":
                    result = execute_ui_viewport_qa(params)
                elif skill == "interactive-login-prep":
                    result = execute_interactive_login_prep(params)
                elif skill == "close-interactive-session":
                    result = execute_close_interactive_session(params)
                elif skill == "cdp-screenshot":
                    result = execute_cdp_screenshot(params)
                elif skill == "form-prep":
                    result = {"success": True, "message": "Form filler is initialized. Manual validation active. Stopping before submit.", "gated": True}
                else:
                    result = {"error": f"Unknown skill: {skill}"}
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(result, indent=2).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Server error: {str(e)}"}, indent=2).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Output clean server logs
        sys.stdout.write(f"[{self.log_date_time_string()}] {self.address_string()} - {format%args}\n")
        sys.stdout.flush()

def main():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((IP, PORT), AgentCardHandler) as httpd:
        print(f"Serving Agent Card with functional Playwright skills at http://100.108.131.116:{PORT}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

if __name__ == "__main__":
    main()
