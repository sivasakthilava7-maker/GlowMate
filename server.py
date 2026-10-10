"""GlowMate Web Application Server.

Pure standard-library multi-threaded HTTP server providing REST API endpoints
and serving the modern, mobile-responsive GlowMate PWA frontend.
Accessible from both desktop/laptop (localhost) and smartphones on local Wi-Fi.
"""

from __future__ import annotations

import json
import mimetypes
import os
import socket
import sys

# Ensure Windows terminal doesn't crash on emoji characters
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agent import GlowMateAgent
from config import load_config

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"


def get_local_ip() -> str:
    """Detect machine's LAN IP address for phone/mobile connection."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually establish connection, but selects outbound network adapter
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


class GlowMateHTTPHandler(SimpleHTTPRequestHandler):
    """Custom request handler with REST API routing and static file serving."""

    agent = GlowMateAgent(load_config())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _send_json_response(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # -------------------------------------------------------------------------
    # GET Endpoints
    # -------------------------------------------------------------------------

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. API Status / Health
        if path == "/api/status":
            local_ip = get_local_ip()
            has_key = self.agent.config.has_api_key
            status_info = {
                "server": "GlowMate Assistant Server",
                "status": "online",
                "has_gemini_key": has_key,
                "model": self.agent.config.model,
                "current_time": self.agent.tracker_tool.get_current_datetime_display(),
                "laptop_url": "http://localhost:8000",
                "phone_url": f"http://{local_ip}:8000",
            }
            return self._send_json_response(status_info)

        # 2. What to Use Right Now
        elif path == "/api/now":
            res = self.agent.handle_what_to_use_now()
            return self._send_json_response(res)

        # 3. User Profile
        elif path == "/api/profile":
            res = self.agent.handle_get_profile()
            return self._send_json_response(res)

        # 4. Reminders Configuration
        elif path == "/api/reminders":
            res = self.agent.handle_get_reminders()
            return self._send_json_response(res)

        # 5. Routine Tracking & Streaks
        elif path == "/api/track":
            res = self.agent.handle_tracking("summary")
            return self._send_json_response(res)

        # 6. Full Routines (Skincare, Haircare, Bodycare)
        elif path == "/api/routine/skincare":
            res = self.agent.handle_skincare_routine()
            return self._send_json_response(res)
        elif path == "/api/routine/haircare":
            res = self.agent.handle_haircare_routine()
            return self._send_json_response(res)
        elif path == "/api/routine/bodycare":
            res = self.agent.handle_bodycare_routine()
            return self._send_json_response(res)

        # 7. Products Catalog Filter
        elif path == "/api/products":
            cat = query.get("category", [None])[0]
            budget = query.get("budget_tier", [None])[0]
            res = self.agent.handle_product_search(category=cat, budget_tier=budget)
            return self._send_json_response(res)

        # 8. Ingredient Lookup
        elif path == "/api/ingredients":
            name = query.get("name", [""])[0]
            res = self.agent.handle_ingredient_query(name)
            return self._send_json_response(res)

        # 9. Nutrition Guide
        elif path == "/api/nutrition":
            name = query.get("nutrient", [None])[0]
            res = self.agent.handle_nutrition_query(name)
            return self._send_json_response(res)

        # 10. Usage Statistics
        elif path == "/api/stats":
            stats = self.agent.client.get_usage_statistics()
            return self._send_json_response({"usage_statistics": stats})

        # Static file fallback (SPA index.html / assets)
        super().do_GET()

    # -------------------------------------------------------------------------
    # POST Endpoints
    # -------------------------------------------------------------------------

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()

        # 1. Update Profile
        if path == "/api/profile":
            updated_profile = self.agent.profile_tool.update_profile(body)
            self.agent.client.clear_cache()
            return self._send_json_response({
                "status": "success",
                "summary": "Profile updated successfully.",
                "profile": updated_profile.to_dict(),
            })

        # 2. Update Reminder Schedule
        elif path == "/api/reminders":
            res = self.agent.handle_set_reminders(body)
            return self._send_json_response(res)

        # 3. Configure Gemini API Key & Model
        elif path == "/api/settings":
            new_key = body.get("gemini_api_key", "").strip()
            new_model = body.get("gemini_model", "").strip() or "gemini-3.8-flash"
            if new_key:
                os.environ["GEMINI_API_KEY"] = new_key
                os.environ["GEMINI_MODEL"] = new_model
                env_path = BASE_DIR / ".env"
                try:
                    with open(env_path, "w", encoding="utf-8") as f:
                        f.write(f"GEMINI_API_KEY={new_key}\nGEMINI_MODEL={new_model}\n")
                except Exception:
                    pass
                self.agent.config = load_config()
                self.agent.client.config = self.agent.config
                return self._send_json_response({
                    "status": "success",
                    "summary": "Gemini API Key configured and activated successfully!",
                    "has_gemini_key": True,
                })
            return self._send_json_response({"status": "error", "message": "API key cannot be empty."}, 400)

        # 3. Log Routine Check-in (AM or PM)
        elif path == "/api/track":
            am = bool(body.get("am", False))
            pm = bool(body.get("pm", False))
            res = self.agent.handle_tracking("log", am=am, pm=pm)
            return self._send_json_response(res)

        # 4. Natural Language Chat / Gemini Consultation
        elif path == "/api/chat":
            prompt = body.get("query", "").strip()
            if not prompt:
                return self._send_json_response({"status": "error", "message": "Query cannot be empty."}, 400)
            res = self.agent.handle_natural_language_query(prompt)
            return self._send_json_response(res)

        # 5. Clear Cache
        elif path == "/api/cache/clear":
            count = self.agent.client.clear_cache()
            return self._send_json_response({"cleared": count})

        self._send_json_response({"error": "Endpoint not found"}, 404)

    # -------------------------------------------------------------------------
    # DELETE Endpoints
    # -------------------------------------------------------------------------

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/profile":
            res = self.agent.handle_delete_profile()
            return self._send_json_response(res)

        self._send_json_response({"error": "Endpoint not found"}, 404)


def run_server(port: int = 8000) -> None:
    """Start the multi-threaded web server on all interfaces."""
    WEB_DIR.mkdir(parents=True, exist_ok=True)
    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, GlowMateHTTPHandler)

    local_ip = get_local_ip()

    print("\n" + "=" * 70)
    print("      [GLOWMATE WEB APP & AUTOMATED ASSISTANT IS LIVE]")
    print("=" * 70)
    print(f"  Laptop / Desktop Access:   http://localhost:{port}")
    print(f"  Phone / Tablet Access:     http://{local_ip}:{port}")
    print("-" * 70)
    print("  To use on your phone: Connect to the same Wi-Fi network and open")
    print(f"  http://{local_ip}:{port} in Safari, Chrome, or your mobile browser.")
    print("  You can tap 'Add to Home Screen' to install it as an app!")
    print("=" * 70 + "\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down GlowMate server gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    env_port = os.environ.get("PORT")
    if env_port and env_port.isdigit():
        port_arg = int(env_port)
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    else:
        port_arg = 8000
    run_server(port_arg)
