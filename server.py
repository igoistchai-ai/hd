import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = int(os.getenv("PORT", "10000"))
DB_PATH = os.getenv("DB_PATH", "bot.db")
ROOT = Path(__file__).resolve().parent

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        username TEXT,
        access_key TEXT UNIQUE NOT NULL,
        robux INTEGER DEFAULT 0,
        nickname TEXT DEFAULT 'Player',
        created_at TEXT NOT NULL,
        active INTEGER DEFAULT 1
    )
    """)
    conn.commit()
    conn.close()

def validate_key(key):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT access_key, robux, nickname, telegram_id FROM keys WHERE access_key=? AND active=1",
        (key,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?",1)[0]
        if path == "/health":
            self.send_json(200, {"ok": True})
            return
        if path in ("/", "/index.html"):
            data = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/login":
            self.send_json(404, {"ok": False, "error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            key = str(body.get("key", "")).strip().upper()
        except Exception:
            self.send_json(400, {"ok": False, "error": "Invalid request"})
            return

        row = validate_key(key)
        if not row:
            self.send_json(401, {"ok": False, "error": "Invalid or inactive access key"})
            return

        self.send_json(200, {
            "ok": True,
            "nickname": row["nickname"],
            "robux": row["robux"]
        })

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)

def start_bot():
    from bot import run_bot
    run_bot()

if __name__ == "__main__":
    init_db()

    if os.getenv("BOT_TOKEN"):
        threading.Thread(target=start_bot, daemon=True).start()
    else:
        print("BOT_TOKEN is not set; website will run without Telegram bot.", flush=True)

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"NEZZX website listening on port {PORT}", flush=True)
    server.serve_forever()
