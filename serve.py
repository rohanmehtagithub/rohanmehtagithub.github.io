#!/usr/bin/env python3
"""Local preview server. Identical to `python3 -m http.server`, except every
response carries Cache-Control: no-store, so the browser re-fetches HTML, CSS
and icons on each load and edits always show up on a plain reload.

    python3 serve.py [port]      (default 8000)
"""
import http.server, os, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

class NoCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()
    def log_message(self, *args):   # keep the terminal quiet
        pass

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
print(f"serving {os.getcwd()} at http://127.0.0.1:{port}/  (no-store)")
http.server.ThreadingHTTPServer(("127.0.0.1", port), NoCache).serve_forever()
