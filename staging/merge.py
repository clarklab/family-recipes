#!/usr/bin/env python3
"""Check the transcription batches in staging/ and merge them into recipes/ and cards.json.

    python3 staging/merge.py            # check only, change nothing
    python3 staging/merge.py --write    # check, then merge

Cards already in cards.json keep their review status. Recipe names that clash with an
existing recipe get the card id appended.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "staging"
RECIPES = ROOT / "recipes"
IMAGES = ROOT / "web-images"
WRITE = "--write" in sys.argv

problems, warnings = [], []


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    meta = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^(\w+):\s*(.*)$", line)
        if kv:
            meta[kv.group(1)] = kv.group(2).strip()
    return meta


existing_cards = json.loads((ROOT / "cards.json").read_text())
existing_ids = {c["id"] for c in existing_cards}
taken_slugs = {p.stem for p in RECIPES.glob("*.md")}

all_images = {p.name for p in IMAGES.glob("*.jpg")}
used_images = {im["file"] for c in existing_cards for im in c["images"]}

new_cards, moves = [], []  # moves: (src path, dest slug, text)
for batch in sorted(STAGING.glob("batch-*")):
    cj = batch / "cards.json"
    if not cj.exists():
        problems.append(f"{batch.name}: no cards.json (still running?)")
        continue
    try:
        cards = json.loads(cj.read_text())
    except json.JSONDecodeError as e:
        problems.append(f"{batch.name}: cards.json is not valid JSON ({e})")
        continue
    renames = {}
    staged = {p.stem: p for p in (batch / "recipes").glob("*.md")}
    referenced = set()
    for card in cards:
        cid = card.get("id")
        if cid in existing_ids or any(c["id"] == cid for c in new_cards):
            problems.append(f"{batch.name}: card {cid} appears twice")
            continue
        card["status"] = "needs-review"
        for im in card.get("images", []):
            if im.get("file") not in all_images:
                problems.append(f"{batch.name}: card {cid} lists missing image {im.get('file')}")
            elif im["file"] in used_images:
                problems.append(f"{batch.name}: image {im['file']} is used by two cards")
            used_images.add(im.get("file"))
            if im.get("rotate", 0) not in (0, 90, 180, 270):
                problems.append(f"{batch.name}: card {cid} has odd rotation {im.get('rotate')}")
        if not card.get("recipes") and not card.get("note"):
            warnings.append(f"{batch.name}: card {cid} has no recipes and no note")
        fixed = []
        for slug in card.get("recipes", []):
            referenced.add(slug)
            src = staged.get(slug)
            if not src:
                problems.append(f"{batch.name}: card {cid} lists recipe {slug} but there is no file")
                continue
            text = src.read_text()
            meta = frontmatter(text)
            if meta is None:
                problems.append(f"{batch.name}: {slug}.md has no front matter")
            else:
                for key in ("title", "card", "tags", "confidence"):
                    if not meta.get(key):
                        problems.append(f"{batch.name}: {slug}.md is missing {key}")
                if meta.get("confidence") not in ("high", "medium", "low"):
                    problems.append(f"{batch.name}: {slug}.md has confidence {meta.get('confidence')!r}")
            for section in ("## Ingredients", "## Directions", "## Notes"):
                if section not in text:
                    warnings.append(f"{batch.name}: {slug}.md has no '{section}' section")
            dest = slug
            if dest in taken_slugs:
                dest = f"{slug}-{cid}"
                n = 2
                while dest in taken_slugs:
                    dest = f"{slug}-{cid}-{n}"
                    n += 1
                renames[slug] = dest
            taken_slugs.add(dest)
            moves.append((src, dest, text))
            fixed.append(dest)
        card["recipes"] = fixed
        new_cards.append(card)
    for slug in set(staged) - referenced:
        warnings.append(f"{batch.name}: {slug}.md isn't listed on any card")
    for old, new in renames.items():
        warnings.append(f"{batch.name}: renamed {old} -> {new} (name already taken)")

unused = sorted(all_images - used_images)
if unused:
    problems.append(f"{len(unused)} scans not on any card: {', '.join(unused)}")

n_rec = len(moves)
conf = {}
for _, _, text in moves:
    c = (frontmatter(text) or {}).get("confidence", "?")
    conf[c] = conf.get(c, 0) + 1
print(f"New cards: {len(new_cards)}   new recipes: {n_rec}   confidence: {conf}")
for w in warnings:
    print("note:", w)
for p in problems:
    print("PROBLEM:", p)

if WRITE:
    if problems:
        sys.exit("Not merging until the problems above are fixed.")
    for src, dest, text in moves:
        (RECIPES / f"{dest}.md").write_text(text if text.endswith("\n") else text + "\n")
    def sort_key(c):
        loose = c["id"].startswith("loose-")
        return (loose, c["id"])
    merged = sorted(existing_cards + new_cards, key=sort_key)
    (ROOT / "cards.json").write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    print(f"Merged. cards.json now has {len(merged)} cards; recipes/ has {len(list(RECIPES.glob('*.md')))} files.")
