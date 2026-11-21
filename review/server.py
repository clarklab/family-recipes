#!/usr/bin/env python3
"""Tiny local server for the recipe review screen.

Run:  python3 review/server.py        (then open http://localhost:8765)

Serves the review page and the web-sized scans, and saves edits straight
back to recipes/*.md and review status to cards.json. Listens on
localhost only.
"""
import json
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "recipes"
CARDS = ROOT / "cards.json"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CARD_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
STATUSES = {"needs-review", "approved", "flagged"}


def load_cards():
    return json.loads(CARDS.read_text(encoding="utf-8"))


def save_cards(cards):
    tmp = CARDS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cards, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(CARDS)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        if self.command != "GET" or "/api/" in self.path:
            super().log_message(fmt, *args)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length).decode("utf-8")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.path = "/review/index.html"
        if self.path == "/api/data":
            cards = load_cards()
            recipes = {}
            for card in cards:
                for slug in card.get("recipes", []):
                    path = RECIPES / f"{slug}.md"
                    recipes[slug] = path.read_text(encoding="utf-8") if path.exists() else ""
            return self.send_json({"cards": cards, "recipes": recipes})
        # Only serve the review page and the web-sized scans.
        if not (self.path.startswith("/review/") or self.path.startswith("/web-images/")):
            return self.send_error(404)
        return super().do_GET()

    def do_PUT(self):
        m = re.fullmatch(r"/api/recipe/([^/]+)", self.path)
        if m:
            slug = m.group(1)
            if not SLUG.match(slug):
                return self.send_json({"error": "bad recipe name"}, 400)
            text = self.read_body().replace("\r\n", "\n")
            if not text.endswith("\n"):
                text += "\n"
            (RECIPES / f"{slug}.md").write_text(text, encoding="utf-8")
            return self.send_json({"ok": True})

        m = re.fullmatch(r"/api/card/([^/]+)", self.path)
        if m:
            card_id = m.group(1)
            if not CARD_ID.match(card_id):
                return self.send_json({"error": "bad card id"}, 400)
            try:
                patch = json.loads(self.read_body())
            except json.JSONDecodeError:
                return self.send_json({"error": "bad json"}, 400)
            cards = load_cards()
            card = next((c for c in cards if c["id"] == card_id), None)
            if card is None:
                return self.send_json({"error": "no such card"}, 404)
            if "status" in patch:
                if patch["status"] not in STATUSES:
                    return self.send_json({"error": "bad status"}, 400)
                card["status"] = patch["status"]
            if "reviewNote" in patch:
                note = str(patch["reviewNote"]).strip()
                if note:
                    card["reviewNote"] = note
                else:
                    card.pop("reviewNote", None)
            save_cards(cards)
            return self.send_json({"ok": True, "card": card})

        return self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Recipe review running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
