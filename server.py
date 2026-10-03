import json
import os
import sqlite3
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("PORT", "10000"))
DB_PATH = os.environ.get("DB_PATH", "bot.db")


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def login_key(key):
    key = (key or "").strip().upper()
    if not key:
        return None, "Enter your access key."

    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            """
            SELECT
                k.access_key,
                k.robux,
                COALESCE(u.profile_name, k.nickname, 'Player') AS nickname
            FROM keys k
            LEFT JOIN users u ON u.telegram_id = k.telegram_id
            WHERE UPPER(k.access_key)=? AND k.active=1
            ORDER BY k.id DESC
            LIMIT 1
            """,
            (key,),
        ).fetchone()
    except sqlite3.Error as exc:
        print(f"Database error: {exc}", flush=True)
        return None, "Database is not ready."

    conn.close()

    if not row:
        return None, "Invalid or inactive access key."

    return {
        "ok": True,
        "access_key": row["access_key"],
        "nickname": row["nickname"] or "Player",
        "robux": int(row["robux"] or 0),
    }, None


class Handler(SimpleHTTPRequestHandler):
    def do_HEAD(self):
        if self.path == "/health":
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return

        if self.path in ("/", ""):
            self.path = "/index.html"

        try:
            with open("index.html", "rb") as f:
                size = os.fstat(f.fileno()).st_size
        except FileNotFoundError:
            self.send_error(404, "index.html not found")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(size))
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/login":
            self.send_error(404, "Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 10000:
                json_response(self, 400, {
                    "ok": False,
                    "error": "Invalid request."
                })
                return

            raw = self.rfile.read(length)
            data = json.loads(raw.decode("utf-8"))
            result, error = login_key(data.get("key", ""))

            if error:
                status = 503 if error == "Database is not ready." else 401
                json_response(self, status, {
                    "ok": False,
                    "error": error
                })
                return

            json_response(self, 200, result)

        except (ValueError, json.JSONDecodeError):
            json_response(self, 400, {
                "ok": False,
                "error": "Invalid JSON."
            })
        except Exception as exc:
            print(f"API error: {exc}", flush=True)
            json_response(self, 500, {
                "ok": False,
                "error": "Server error."
            })

    def do_GET(self):
        if self.path == "/health":
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path in ("/", ""):
            self.path = "/index.html"

        return super().do_GET()

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


def run_web():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"NEZZX website listening on port {PORT}", flush=True)

    try:
        server.serve_forever()
    finally:
        server.server_close()


def main():
    web_thread = threading.Thread(
        target=run_web,
        name="web-server",
        daemon=True,
    )
    web_thread.start()

    print("Starting Telegram bot in MAIN THREAD...", flush=True)

    from bot import main as run_bot
    run_bot()


if __name__ == "__main__":
    main()
