#!/usr/bin/env python3
"""
host_agent_card.py — Merged & Production-Ready A2A Server
Consolidates:
  1. Astra's Proposed Fixes v1 (P0 Threading, P0 SingletonLock, Task registry, RFI stubs)
  2. Our Active Chrome CDP Screen Capturer (CDP debugging mode)
"""

import json
import http.server
import socketserver
import threading
import urllib.parse
from pathlib import Path
import sys
import subprocess
import time

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError  # type: ignore[import]
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    sync_playwright = None  # type: ignore[assignment]
    PlaywrightTimeoutError = Exception  # type: ignore[assignment,misc]
    PLAYWRIGHT_AVAILABLE = False

PORT = 9999
IP = "0.0.0.0"

ROOT_DIR = Path("/Users/kirk/operator-prototype")
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
PROFILE_DIR = ROOT_DIR / "chrome-profile"
SCRIPT_DIR = Path(__file__).parent  # Relative path, works wherever repo lives

ARTIFACTS_DIR.mkdir(exist_ok=True, parents=True)
PROFILE_DIR.mkdir(exist_ok=True, parents=True)

# Task state registry for RFI loop
ACTIVE_TASKS = {}  # task_id -> {"state": str, "event": threading.Event, "inputs": dict}
ACTIVE_TASKS_LOCK = threading.Lock()

# Clean capabilities & skills manifest
CARD_DATA = {
    "name": "Ironborn Archer (Local)",
    "description": "Kirk's local execution agent — browser control, form filling, visual QA, and interactive login handoff over Tailscale.",
    "url": f"http://100.108.131.116:{PORT}",
    "version": "1.1.0",
    "provider": {
        "organization": "Kirk Truax",
        "url": "https://agentlocker.io"
    },
    "capabilities": {
        "streaming": True,
        "pushNotifications": False,
        "cdp_mode": True,  # True because we support connect_over_cdp
        "artifacts_base_url": f"http://100.108.131.116:{PORT}/artifacts/",
        "rfi_supported": True   # Supports TASK_STATE_SUSPENDED_WAITING_ON_PEER protocol
    },
    "skills": [
        {
            "id": "browser-read",
            "name": "Local Browser Browse and Read (Read-Only)",
            "description": "Navigates to any public web page, extracts visible text, captures full-page screenshot. Returns text and screenshot_url.",
            "tags": ["browser", "read-only", "screenshot", "scraping"],
            "returns": ["text", "title", "screenshot_url"],
            "examples": [
                "Go to https://example.com, read its text content, and take a screenshot.",
                "Browse the Greenhouse application page for software engineers and capture the form layout."
            ],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"]
        },
        {
            "id": "ui-viewport-qa",
            "name": "Multi-Viewport Visual QA Layout Tester",
            "description": "Launches any local or public URL at standard mobile/tablet/desktop viewports and captures layout screenshots.",
            "tags": ["visual-qa", "viewports", "layout", "mobile-first"],
            "viewports": ["iphone:390x844", "ipad:820x1180", "desktop:1280x900"],
            "returns": ["screenshot_url", "device", "viewport"],
            "examples": [
                "Take visual QA screenshots of localhost:3000 at iPhone and iPad viewports."
            ],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"]
        },
        {
            "id": "interactive-login-prep",
            "name": "Interactive Login Preparer (MFA & Password Gate)",
            "description": "Launches a visible browser, navigates to login page, inputs username, focuses password field, takes screenshot. Browser stays open for Kirk to complete login manually.",
            "tags": ["login", "mfa-gate", "human-in-the-loop", "interactive"],
            "gate": "password-and-mfa",
            "returns": ["screenshot_url", "message"],
            "examples": [
                "Go to LinkedIn login page and prepare a login session for kirk@example.com."
            ],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"]
        },
        {
            "id": "close-interactive-session",
            "name": "Close Active Interactive Browser Session",
            "description": "Forces the currently running visible interactive browser window to close, freeing resources.",
            "tags": ["browser", "cleanup", "interactive"],
            "returns": ["success", "message"],
            "inputModes": ["application/json"],
            "outputModes": ["application/json"]
        },
        {
            "id": "resume-interactive-session",
            "name": "Resume Suspended Task (RFI Response)",
            "description": "Resumes a task suspended at a TASK_STATE_SUSPENDED_WAITING_ON_PEER state. Accepts taskId, rfiId, and inputs dict. Unblocks the waiting browser thread.",
            "tags": ["rfi", "resume", "human-in-the-loop"],
            "requires": ["taskId", "rfiId", "inputs"],
            "returns": ["success", "message"],
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


def _clear_singleton_lock():
    """Clear ChromeDriver SingletonLock before browser launch."""
    singleton_lock = PROFILE_DIR / "SingletonLock"
    if singleton_lock.exists():
        print("[startup] Clearing stale SingletonLock before browser launch")
        try:
            singleton_lock.unlink()
        except Exception as e:
            print(f"[startup] Warning: could not unlink SingletonLock: {e}")


def execute_browser_read(params):
    url = params.get("url")
    if not url:
        return {"error": "Missing 'url' parameter"}

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "Playwright not available in this environment"}

    _clear_singleton_lock()

    print(f"[browser-read] Navigating to: {url}")
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=False,
                viewport={"width": 1280, "height": 900},
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)

            title = page.title()
            text = page.locator("body").inner_text(timeout=5000)[:3000]

            safe_name = "".join(c for c in url if c.isalnum() or c in ".-_")[:40] + ".png"
            screenshot_path = ARTIFACTS_DIR / safe_name
            page.screenshot(path=str(screenshot_path), full_page=True)

            context.close()

            return {
                "success": True,
                "title": title,
                "text": text,
                "screenshot_url": f"http://100.108.131.116:{PORT}/artifacts/{safe_name}"
            }
    except Exception as e:
        return {"error": f"Playwright execution failed: {str(e)}"}


def execute_ui_viewport_qa(params):
    url = params.get("url", "http://localhost:3000")
    device = params.get("device", "ipad")

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "Playwright not available in this environment"}

    viewports = {
        "iphone": {"width": 390, "height": 844, "is_mobile": True},
        "ipad":   {"width": 820, "height": 1180, "is_mobile": True},
        "desktop":{"width": 1280, "height": 900, "is_mobile": False}
    }
    vp = viewports.get(device, viewports["ipad"])

    _clear_singleton_lock()

    print(f"[ui-viewport-qa] URL: {url}, device: {device}")
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
            page.wait_for_timeout(1000)

            safe_name = f"qa-{device}-" + "".join(c for c in url if c.isalnum() or c in ".-_")[:30] + ".png"
            screenshot_path = ARTIFACTS_DIR / safe_name
            page.screenshot(path=str(screenshot_path))

            context.close()

            return {
                "success": True,
                "device": device,
                "viewport": vp,
                "screenshot_url": f"http://100.108.131.116:{PORT}/artifacts/{safe_name}"
            }
    except Exception as e:
        return {"error": f"Playwright QA execution failed: {str(e)}"}


ACTIVE_LOGIN_PREP_PROCESS = None
ACTIVE_LOGIN_PREP_LOCK = threading.Lock()


def execute_interactive_login_prep(params):
    global ACTIVE_LOGIN_PREP_PROCESS
    url = params.get("url")
    username = params.get("username", "")

    if not url:
        return {"error": "Missing 'url' parameter"}

    print(f"[interactive-login-prep] URL: {url}, username: {username}")

    with ACTIVE_LOGIN_PREP_LOCK:
        if ACTIVE_LOGIN_PREP_PROCESS and ACTIVE_LOGIN_PREP_PROCESS.poll() is None:
            try:
                ACTIVE_LOGIN_PREP_PROCESS.terminate()
                ACTIVE_LOGIN_PREP_PROCESS.wait(timeout=2)
            except Exception as e:
                print(f"[interactive-login-prep] Error terminating previous process: {e}")

        python_path = str(ROOT_DIR / ".venv" / "bin" / "python")
        script_path = str(SCRIPT_DIR / "run_login_prep.py")

        cmd = [python_path, script_path, "--url", url]
        if username:
            cmd.extend(["--username", username])

        try:
            proc = subprocess.Popen(cmd)
            ACTIVE_LOGIN_PREP_PROCESS = proc
        except Exception as e:
            return {"error": f"Failed to start login prep process: {str(e)}"}

    time.sleep(5)  # Give browser time to open and navigate

    screenshot_url = f"http://100.108.131.116:{PORT}/artifacts/login-prep.png"
    return {
        "success": True,
        "message": "Interactive login session prepared. Browser is open on Kirk's screen for manual takeover.",
        "screenshot_url": screenshot_url
    }


def execute_close_interactive_session(params):
    global ACTIVE_LOGIN_PREP_PROCESS
    with ACTIVE_LOGIN_PREP_LOCK:
        if ACTIVE_LOGIN_PREP_PROCESS and ACTIVE_LOGIN_PREP_PROCESS.poll() is None:
            try:
                ACTIVE_LOGIN_PREP_PROCESS.terminate()
                ACTIVE_LOGIN_PREP_PROCESS.wait(timeout=3)
                ACTIVE_LOGIN_PREP_PROCESS = None
                return {"success": True, "message": "Browser window closed."}
            except Exception:
                pass

        subprocess.run(["pkill", "-f", "run_login_prep.py"], capture_output=True)
        ACTIVE_LOGIN_PREP_PROCESS = None
        return {"success": True, "message": "Sweep complete — any orphaned browser windows closed."}


def execute_resume_interactive_session(params):
    """RFI resume handler — unblocks a suspended browser task."""
    task_id = params.get("taskId")
    rfi_id = params.get("rfiId")
    inputs = params.get("inputs", {})

    if not task_id:
        return {"error": "Missing taskId"}

    with ACTIVE_TASKS_LOCK:
        task = ACTIVE_TASKS.get(task_id)

    if not task:
        return {"error": f"No active task found with taskId: {task_id}"}

    task["inputs"] = inputs
    task["state"] = "RESUMING"
    task["event"].set()  # Unblocks the waiting browser thread

    return {
        "success": True,
        "message": f"Task {task_id} resumed with {len(inputs)} input(s). Browser thread unblocked."
    }


def execute_cdp_screenshot(params):
    """Connect over Chrome DevTools Protocol (CDP) and snap active page."""
    cdp_url = params.get("cdp_url", "http://localhost:9222")
    
    # Safely clear the active singleton lock to prevent issues
    _clear_singleton_lock()
    
    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "Playwright not available in this environment"}
        
    print(f"[cdp-screenshot] Connecting over CDP to: {cdp_url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]

            # Find the active/focused tab instead of always grabbing pages[0]
            active_page = None
            for p in context.pages:
                try:
                    if p.evaluate("document.hasFocus()"):
                        active_page = p
                        break
                except Exception:
                    continue
            # Fallback: last opened tab (most recent), then first
            if active_page is None:
                active_page = context.pages[-1] if context.pages else context.new_page()
            page = active_page

            title = page.title()
            url = page.url
            
            safe_name = "cdp-screenshot.png"
            screenshot_path = ARTIFACTS_DIR / safe_name
            page.screenshot(path=str(screenshot_path))
            
            browser.close()
            
            return {
                "success": True,
                "title": title,
                "url": url,
                "screenshot_url": f"http://100.108.131.116:{PORT}/artifacts/{safe_name}"
            }
    except Exception as e:
        return {"error": f"CDP connect failed: {str(e)}"}


# Threaded server — handles concurrent requests while browser tasks run
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


class AgentCardHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path in ["/", "/.well-known/agent-card.json", "/agent-card.json"]:
            self._respond_json(200, CARD_DATA)

        elif self.path.startswith("/artifacts/"):
            filename = Path(self.path.replace("/artifacts/", "")).name  # prevent traversal
            file_path = ARTIFACTS_DIR / filename
            if file_path.is_file():
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(file_path.read_bytes())
            else:
                self._respond_text(404, "Screenshot not found")
        else:
            self._respond_text(404, "Not Found")

    def do_POST(self):
        if self.path == "/execute":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                payload = json.loads(post_data.decode("utf-8"))
                skill = payload.get("skill")
                params = payload.get("params", {})

                dispatch = {
                    "browser-read":               execute_browser_read,
                    "ui-viewport-qa":             execute_ui_viewport_qa,
                    "interactive-login-prep":     execute_interactive_login_prep,
                    "close-interactive-session":  execute_close_interactive_session,
                    "resume-interactive-session": execute_resume_interactive_session,
                    "cdp-screenshot":             execute_cdp_screenshot,
                    "form-prep":                  lambda p: {"error": "form-prep not yet implemented — removed from card"},
                }

                handler = dispatch.get(skill)
                if handler:
                    result = handler(params)
                else:
                    result = {"error": f"Unknown skill: '{skill}'. Available: {list(dispatch.keys())}"}

                self._respond_json(200, result)

            except Exception as e:
                self._respond_json(500, {"error": f"Server error: {str(e)}"})
        else:
            self._respond_text(404, "Not Found")

    def _respond_json(self, code, data):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _respond_text(self, code, text):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def log_message(self, format, *args):
        sys.stdout.write(f"[{self.log_date_time_string()}] {self.address_string()} — {format % args}\n")
        sys.stdout.flush()


def main():
    # Startup banner
    print("=" * 60)
    print(f"  IronbornArcher A2A Server — v{CARD_DATA['version']}")
    print(f"  Listening on http://0.0.0.0:{PORT}/")
    print(f"  Artifacts dir : {ARTIFACTS_DIR} {'✅' if ARTIFACTS_DIR.exists() else '❌'}")
    print(f"  Chrome profile: {PROFILE_DIR} {'✅' if PROFILE_DIR.exists() else '❌'}")
    print(f"  SingletonLock : {'⚠️  PRESENT — will be cleared on first launch' if (PROFILE_DIR / 'SingletonLock').exists() else '✅ Clear'}")
    print(f"  Playwright    : {'✅ Available' if PLAYWRIGHT_AVAILABLE else '❌ Not installed'}")
    print(f"  Skills        : {[s['id'] for s in CARD_DATA['skills']]}")
    print("=" * 60)

    with ThreadedTCPServer((IP, PORT), AgentCardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[server] Shutting down.")


if __name__ == "__main__":
    main()
