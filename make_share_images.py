#!/usr/bin/env python3
"""Render the share image (og.png) and app icons into site-src/ with headless Chrome.

    python3 make_share_images.py      # then: python3 build_site.py

Only needed when site-src/_og.html or site-src/favicon.svg change. _og.html uses
card photos from site/cards/thumb/, so build the site once first.
"""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "site-src"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def shot(page, out, w, h, query="", transparent=False):
    with tempfile.TemporaryDirectory() as profile:
        cmd = [CHROME, "--headless=new", f"--user-data-dir={profile}", "--hide-scrollbars",
               "--force-device-scale-factor=1", f"--window-size={w},{h}", "--virtual-time-budget=6000",
               f"--screenshot={out}"]
        if transparent:
            cmd.append("--default-background-color=00000000")
        cmd.append((SRC / page).as_uri() + query)
        subprocess.run(cmd, check=True, capture_output=True)
    print("wrote", out.relative_to(ROOT))


def shrink(src, out, size):
    subprocess.run(["magick", str(src), "-resize", f"{size}x{size}", str(out)], check=True)
    print("wrote", out.relative_to(ROOT))


# Chrome won't make windows smaller than ~500px, so icons render at 512 and get scaled down.
shot("_og.html", SRC / "og.png", 1200, 630)
shot("_icon.html", SRC / "icon-512.png", 512, 512, "?bg=1&k=0.86")
shot("_icon.html", SRC / "icon-512-maskable.png", 512, 512, "?bg=1&k=0.66")
shot("_icon.html", SRC / "_touch.png", 512, 512, "?bg=1&k=0.8")
shot("_icon.html", SRC / "_fav.png", 512, 512, "?k=1", transparent=True)
shrink(SRC / "icon-512.png", SRC / "icon-192.png", 192)
shrink(SRC / "_touch.png", SRC / "apple-touch-icon.png", 180)
subprocess.run(["magick", str(SRC / "_fav.png"), "-define", "icon:auto-resize=32,16", str(SRC / "favicon.ico")], check=True)
print("wrote site-src/favicon.ico")
for tmp in ("_touch.png", "_fav.png"):
    (SRC / tmp).unlink()
