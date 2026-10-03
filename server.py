import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


PORT = int(os.environ.get("PORT", "10000"))


class Handler(SimpleHTTPRequestHandler):
    """Small Render-compatible HTTP server for the website."""

    def do_HEAD(self):
        if self.path == "/health":
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return

        if self.path == "/" or self.path == "":
            self.path = "/index.html"

        try:
            f = open("index.html", "rb")
        except FileNotFoundError:
            self.send_error(404, "index.html not found")
            return

        try:
            size = os.fstat(f.fileno()).st_size
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(size))
            self.end_headers()
        finally:
            f.close()

    def do_GET(self):
        if self.path == "/health":
            body = b"OK"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/" or self.path == "":
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
    # IMPORTANT:
    # Render may start this process normally, but python-telegram-bot's
    # run_polling() MUST stay in the MAIN THREAD.
    #
    # So the website runs in a daemon thread,
    # while the Telegram bot runs in the main thread.
    web_thread = threading.Thread(
        target=run_web,
        name="web-server",
        daemon=True,
    )
    web_thread.start()

    print("Starting Telegram bot in MAIN THREAD...", flush=True)

    from bot import main as run_bot

    # Never wrap run_bot() in threading.Thread().
    run_bot()


if __name__ == "__main__":
    main()
