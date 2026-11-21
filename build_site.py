#!/usr/bin/env python3
"""Build the recipe website into site/.

    python3 build_site.py

Reads recipes/*.md and cards.json, copies the page files from site-src/, writes
site/recipes.js (all recipe data), and makes upright web copies of each card's
scans in site/cards/ (plus thumbnails). Cards with no recipe and blank backs are
left out. Re-run after editing any recipe; images that already exist are reused.
"""
import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "site-src"
OUT = ROOT / "site"
IMAGES = ROOT / "web-images"


def parse_recipe(path):
    text = path.read_text(encoding="utf-8")
    fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = {}
    for line in fm.group(1).splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("[") and val.endswith("]") and key == "tags":
            val = [t.strip() for t in val[1:-1].split(",") if t.strip()]
        elif len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            val = val[1:-1]
        meta[key] = val

    sections = {"ingredients": [], "directions": [], "notes": []}
    current, group = None, None
    for line in text[fm.end():].splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            name = line[3:].strip().lower()
            current = name if name in sections else None
            group = None
            continue
        if current is None or not line.strip():
            continue
        if line.startswith("### "):
            group = {"heading": line[4:].strip(), "items": []}
            sections[current].append(group)
            continue
        m = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", line)
        item = m.group(1) if m else line.strip()
        if current == "notes":
            sections["notes"].append(item)
            continue
        if group is None:
            group = {"heading": None, "items": []}
            sections[current].append(group)
        group["items"].append(item)

    return {
        "slug": path.stem,
        "title": meta.get("title", path.stem),
        "from": meta.get("from"),
        "card": meta.get("card"),
        "tags": meta.get("tags", []),
        "ingredients": sections["ingredients"],
        "directions": sections["directions"],
        "notes": sections["notes"],
    }


def make_image(job):
    src, full, thumb, rotate = job
    if not full.exists():
        cmd = ["magick", str(src)]
        if rotate:
            cmd += ["-rotate", str(rotate)]
        cmd += ["-resize", "1800x1800>", "-quality", "80", "-strip", str(full)]
        subprocess.run(cmd, check=True)
    if not thumb.exists():
        subprocess.run(["magick", str(full), "-resize", "520x520>", "-quality", "72", "-strip", str(thumb)], check=True)


def main():
    cards = json.loads((ROOT / "cards.json").read_text(encoding="utf-8"))
    card_of = {slug: c for c in cards for slug in c.get("recipes", [])}

    if OUT.exists():
        for p in OUT.iterdir():
            if p.name != "cards":  # keep already-made images
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    (OUT / "cards" / "thumb").mkdir(parents=True, exist_ok=True)
    for p in SRC.iterdir():
        shutil.copy2(p, OUT / p.name)

    recipes, jobs, used = [], [], set()
    for path in sorted((ROOT / "recipes").glob("*.md")):
        r = parse_recipe(path)
        card = card_of.get(r["slug"])
        if not card:
            print(f"skipping {r['slug']}: not on any card")
            continue
        r["card"] = card["id"]
        r["images"] = []
        for im in card["images"]:
            if (im.get("note") or "").lower().startswith("blank"):
                continue
            name = im["file"]
            r["images"].append({"file": name, "label": im.get("label", "")})
            if name not in used:
                used.add(name)
                jobs.append((IMAGES / name, OUT / "cards" / name, OUT / "cards" / "thumb" / name, im.get("rotate", 0)))
        r["sameCard"] = [s for s in card["recipes"] if s != r["slug"]]
        recipes.append(r)

    # Remove images no longer used (e.g. a recipe was deleted).
    for p in (OUT / "cards").rglob("*.jpg"):
        if p.name not in used:
            p.unlink()
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(make_image, jobs))

    recipes.sort(key=lambda r: re.sub(r"[^a-z0-9 ]", "", r["title"].lower().replace("[", "").replace("?]", "")))
    data = json.dumps(recipes, ensure_ascii=False, separators=(",", ":"))
    (OUT / "recipes.js").write_text(f"window.RECIPES = {data};\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
    print(f"Built site/ with {len(recipes)} recipes and {len(used)} card images ({size:.0f} MB).")


if __name__ == "__main__":
    main()
