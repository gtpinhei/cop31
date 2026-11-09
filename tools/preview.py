#!/usr/bin/env python3
"""Local editorial preview: serves the site plus the private drafts, on this machine only.

  python3 -I tools/preview.py [PORT]     then open http://127.0.0.1:PORT/?preview=1#hoje

Drafts come from the private store through /__private__/ and exist only while this process runs on
127.0.0.1. The public site has no such path, and the page only asks for it on localhost, so ?preview=1
is a convenience flag, not access control: the protection is that drafts are never on the server.
"""
import http.server, json, pathlib, sys, functools

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True   # never leave files in the site tree
sys.path.insert(0, str(ROOT / "tools"))
import private as P  # noqa: E402


class H(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/__private__/"):
            store = P.ensure()
            rel = path[len("/__private__/"):]
            if rel == "drafts.json":
                target = store / "drafts.json"
            elif rel.startswith("articles/") and rel.endswith(".json") and "/" not in rel[9:] and ".." not in rel:
                target = store / "articles" / rel[9:]
            else:
                return self.send_error(404)
            body = target.read_bytes() if target.exists() else json.dumps({"schema": 1, "entries": []}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def log_message(self, *a):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(H, directory=str(ROOT)))
    print(f"preview on http://127.0.0.1:{port}/?preview=1#hoje (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
