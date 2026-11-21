#!/usr/bin/env python3
"""Build the recipe website into site/.

    python3 build_site.py

Reads recipes/*.md and cards.json and writes a static site:

  site/index.html          home: search + A-to-Z index (pre-rendered, so it works for crawlers)
  site/r/<slug>/index.html one page per recipe, with meta tags, Open Graph and Recipe JSON-LD
  site/404.html, sitemap.xml, robots.txt, site.webmanifest
  site/cards/              upright web copies of each card's scans (+ thumb/), blank backs left out

Page styles, script, favicons and the share image come from site-src/.
Re-run after editing any recipe; card images that already exist are reused.
"""
import html
import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "site-src"
OUT = ROOT / "site"
IMAGES = ROOT / "web-images"

SITE_URL = "https://recipes.burchreunion.com"
SITE_NAME = "Grammie’s Recipes"
SITE_DESC = ("The family recipe box, typed up from the original cards: cakes, pies, candy, "
             "casseroles and more, each with a photo of the card it came from.")

UNSURE = re.compile(r"\[([^\]\n]+?)\?\]")


# ---------- reading recipes ----------
def parse_recipe(path):
    text = path.read_text(encoding="utf-8")
    fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = {}
    for line in fm.group(1).splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "tags" and val.startswith("[") and val.endswith("]"):
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
        "tags": meta.get("tags", []),
        **sections,
    }


# ---------- text helpers ----------
def plain(s):
    return UNSURE.sub(r"\1", s or "")


def esc(s):
    return html.escape(s or "", quote=True)


def sort_key(r):
    return re.sub(r"[^a-z0-9 ]", "", plain(r["title"]).lower())


def inline(s, self_slug, by_card, prefix):
    """Escape text, mark hard-to-read words, and link "card 0084" to that card's recipe."""
    out = UNSURE.sub(lambda m: f'<span class="unsure" title="Hard to read on the original card">{m.group(1)}</span>',
                     esc(s))

    def link_ids(m):
        def one(idm):
            cid = idm.group(0)
            targets = [r for r in by_card.get(cid, []) if r["slug"] != self_slug]
            if not targets:
                return cid
            t = targets[0]
            return f'<a href="{prefix}r/{t["slug"]}/" title="{esc(plain(t["title"]))}">{cid}</a>'
        return m.group(1) + " " + re.sub(r"\d{4}|loose-\d+", one, m.group(2))

    return re.sub(r"\b(cards?)\s+((?:(?:\d{4}|loose-\d+)(?:,\s*|\s+and\s+)?)+)", link_ids, out)


def describe(r):
    """A plain one-or-two sentence description for search results and link previews."""
    title = plain(r["title"])
    who = f" from the kitchen of {plain(r['from'])}" if r.get("from") else ""
    items = [plain(i) for g in r["ingredients"] for i in g["items"]]
    text = f"{title}{who}, from Grammie’s recipe box. "
    if items:
        text += "Ingredients: " + ", ".join(items) + "."
    if len(text) > 158:
        text = text[:155].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text


# ---------- page pieces ----------
def head(title, desc, path, image, image_alt, prefix, og_type="website", extra=""):
    url = SITE_URL + path
    img = image if image.startswith("http") else SITE_URL + image
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#ece2cc">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:alt" content="{esc(image_alt)}">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{img}">
<link rel="icon" href="{prefix}favicon.ico" sizes="32x32">
<link rel="icon" href="{prefix}favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{prefix}apple-touch-icon.png">
<link rel="manifest" href="{prefix}site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Special+Elite&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{prefix}style.css">
{extra}</head>"""


LIGHTBOX = """
<div class="lightbox" id="lightbox" hidden role="dialog" aria-modal="true" aria-label="Original recipe card">
  <div class="lb-stage" id="lbStage"><img id="lbImg" alt=""></div>
  <div class="lb-bar">
    <button class="lb-btn" id="lbPrev" aria-label="Previous side">←</button>
    <span class="lb-label" id="lbLabel"></span>
    <button class="lb-btn" id="lbNext" aria-label="Next side">→</button>
    <span class="lb-hint">scroll or tap to zoom · drag to look around</span>
    <button class="lb-btn lb-close" id="lbClose" aria-label="Close">✕ close</button>
  </div>
</div>"""


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"


def home_page(recipes, card_count, chips, people):
    rows, letter = [], ""
    for r in recipes:
        first = (sort_key(r)[:1] or "#").upper()
        if first != letter:
            letter = first
            rows.append(f'<div class="letter">{esc(letter)}</div>')
        seen, kind = set(), []
        for t in r["tags"]:
            k = re.sub(r"s\b", "", t.lower())
            if k not in seen:
                seen.add(k)
                kind.append(t)
        rows.append(
            f'<a class="entry" href="r/{r["slug"]}/" data-slug="{r["slug"]}">'
            f'<span class="t">{inline(r["title"], r["slug"], {}, "")}</span>'
            f'<span class="who">{esc(plain(r.get("from") or ""))}</span>'
            f'<span class="kind">{esc(" · ".join(kind[:5]))}</span></a>')
    chip_html = "".join(f'<a class="chip" href="?q={esc(c)}" data-q="{esc(c)}">{esc(c)}<small>{n}</small></a>'
                        for c, n in chips)
    people_html = "".join(f'<a class="chip" href="?q={esc(p)}" data-q="{esc(p)}">{esc(p)}</a>' for p in people)
    ld = jsonld({
        "@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/",
        "description": SITE_DESC,
        "potentialAction": {"@type": "SearchAction", "target": SITE_URL + "/?q={search_term_string}",
                            "query-input": "required name=search_term_string"},
    })
    return head(SITE_NAME, SITE_DESC, "/", "/og.png",
                "Grammie’s Recipes, typed on an index card beside old handwritten recipe cards", "", extra=ld) + f"""
<body data-page="home">
<main class="wrap">
  <header class="masthead">
    <h1>Grammie’s Recipes</h1>
    <p>{len(recipes)} recipes from the family recipe box, typed up from {card_count} original cards.</p>
  </header>
  <form class="search" role="search" action="./" method="get">
    <label for="q">Look something up</label>
    <input id="q" name="q" type="search" autocomplete="off" spellcheck="false" placeholder="chicken, cake, pecans, Viki…">
    <button class="clear" id="clear" type="button" hidden aria-label="Clear search">clear ✕</button>
  </form>
  <nav class="shelf" aria-label="Popular"><span class="lead">Try:</span>{chip_html}</nav>
  {f'<nav class="shelf" aria-label="From the kitchen of"><span class="lead">From the kitchen of:</span>{people_html}</nav>' if people else ''}
  <div class="results-head"><span id="count">All {len(recipes)} recipes, A to Z</span><button class="surprise" id="surprise" type="button">surprise me</button></div>
  <section class="index" id="list">
    {"".join(rows)}
    <p class="empty" id="empty" hidden></p>
  </section>
  <footer class="foot">Every recipe links to a photo of its original card.</footer>
</main>
<script src="recipes.js"></script>
<script src="app.js"></script>
</body>
</html>
"""


def recipe_page(r, by_slug, by_card):
    p = "../../"
    il = lambda s: inline(s, r["slug"], by_card, p)
    title = plain(r["title"])

    def groups(gs, ordered):
        tag = "ol" if ordered else "ul"
        return "".join((f"<h3>{il(g['heading'])}</h3>" if g["heading"] else "") +
                       f"<{tag}>" + "".join(f"<li>{il(i)}</li>" for i in g["items"]) + f"</{tag}>" for g in gs)

    body = ""
    if r["ingredients"]:
        body += "<h2>Ingredients</h2>" + groups(r["ingredients"], False)
    if r["directions"]:
        body += "<h2>Directions</h2>" + groups(r["directions"], True)
    if r["notes"]:
        body += '<h2>Notes</h2><ul class="notes">' + "".join(f"<li>{il(n)}</li>" for n in r["notes"]) + "</ul>"

    same = [by_slug[s] for s in r["sameCard"] if s in by_slug]
    photos = "".join(
        f'<button class="photo" type="button" data-full="{p}cards/{esc(im["file"])}" data-label="{esc(im["label"])}">'
        f'<img src="{p}cards/thumb/{esc(im["file"])}" alt="{esc(title)}, {esc(im["label"] or "card")}" loading="lazy">'
        f'<span class="cap">{esc(im["label"])}</span></button>' for im in r["images"])

    image = f"/cards/{r['images'][0]['file']}" if r["images"] else "/og.png"
    desc = describe(r)
    ld = {
        "@context": "https://schema.org", "@type": "Recipe", "name": title, "description": desc,
        "url": f"{SITE_URL}/r/{r['slug']}/",
        "image": [f"{SITE_URL}/cards/{im['file']}" for im in r["images"]] or [f"{SITE_URL}/og.png"],
        "recipeIngredient": [plain(i) for g in r["ingredients"] for i in g["items"]],
        "recipeInstructions": [{"@type": "HowToStep", "text": plain(((g["heading"] + ": ") if g["heading"] else "") + i)}
                               for g in r["directions"] for i in g["items"]],
        "keywords": ", ".join(r["tags"]),
        "isPartOf": {"@type": "WebSite", "name": SITE_NAME, "url": SITE_URL + "/"},
    }
    if r["tags"]:
        ld["recipeCategory"] = r["tags"][0]
    if r.get("from"):
        ld["author"] = {"@type": "Person", "name": plain(r["from"]).split("/")[-1].strip()}
    else:
        ld["author"] = {"@type": "Organization", "name": "The Burch family"}

    return head(f"{title} · {SITE_NAME}", desc, f"/r/{r['slug']}/", image,
                f"The original handwritten or typed card for {title}", p, "article", jsonld(ld)) + f"""
<body data-page="recipe" data-slug="{r['slug']}" data-title="{esc(title)}">
<main class="wrap">
  <nav class="topnav">
    <a href="{p}" id="back">← the recipe box</a>
    <button id="print" type="button">print this recipe</button>
  </nav>
  <article class="card">
    <header class="card-head">
      <h1>{il(r['title'])}</h1>
      {f'<div class="from">From the kitchen of {il(r["from"])}</div>' if r.get("from") else ""}
    </header>
    <div class="card-body">{body}</div>
  </article>
  {'<div class="filed">Filed under: ' + " ".join(f'<a href="{p}?q={esc(t)}">{esc(t)}</a>' for t in r["tags"]) + "</div>" if r["tags"] else ""}
  {'<div class="also">Also on this card: ' + ", ".join(f'<a href="{p}r/{s["slug"]}/">{esc(plain(s["title"]))}</a>' for s in same) + "</div>" if same else ""}
  {f'''<section class="receipts">
    <h2>The original card</h2>
    <p>Tap a picture to see it up close.</p>
    <div class="photos">{photos}</div>
  </section>''' if photos else ""}
</main>
{LIGHTBOX}
<script src="{p}app.js"></script>
</body>
</html>
"""


def not_found_page():
    return head(f"Not found · {SITE_NAME}", SITE_DESC, "/404.html", "/og.png", "Grammie’s Recipes", "/") + """
<body data-page="404">
<main class="wrap">
  <header class="masthead">
    <h1>Not in the box</h1>
    <p>That recipe card isn’t here. It may have been filed under a different name.</p>
    <p><a href="/">← back to the recipe box</a></p>
  </header>
</main>
<script src="/app.js"></script>
</body>
</html>
"""


# ---------- images ----------
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

    OUT.mkdir(exist_ok=True)
    for p in OUT.iterdir():
        if p.name != "cards":  # keep already-made images
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    (OUT / "cards" / "thumb").mkdir(parents=True, exist_ok=True)
    for p in SRC.iterdir():
        if p.is_file() and not p.name.startswith("_"):
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
    recipes.sort(key=sort_key)

    for p in (OUT / "cards").rglob("*.jpg"):
        if p.name not in used:
            p.unlink()
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(make_image, jobs))

    by_slug = {r["slug"]: r for r in recipes}
    by_card = {}
    for r in recipes:
        by_card.setdefault(r["card"], []).append(r)

    # Search data for the home page (only what search needs).
    search_data = [{
        "slug": r["slug"], "title": r["title"], "from": r.get("from"), "tags": r["tags"],
        "ingredients": " ".join([g["heading"] or "" for g in r["ingredients"]] + [i for g in r["ingredients"] for i in g["items"]]),
        "notes": " ".join(r["notes"]),
        "directions": " ".join(i for g in r["directions"] for i in g["items"]),
    } for r in recipes]
    (OUT / "recipes.js").write_text(
        "window.RECIPES = " + json.dumps(search_data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")

    # Popular searches and people, computed the same way the page searches.
    def count(term):
        t = term.lower()
        return sum(1 for r in recipes if t in " ".join([plain(r["title"]), " ".join(r["tags"]),
                                                          " ".join(i for g in r["ingredients"] for i in g["items"])]).lower())
    chip_terms = ["cake", "cookies", "pie", "candy", "fudge", "bread", "salad", "casserole", "chili", "soup",
                  "chicken", "beef", "chocolate", "apple", "pineapple", "cheese", "pecans", "corn", "green chili", "christmas"]
    chips = [(c, count(c.rstrip("s"))) for c in chip_terms]
    chips = [(c, n) for c, n in chips if n >= 2]
    people = sorted({x.strip() for r in recipes if r.get("from") for x in plain(r["from"]).split("/")
                     if x.strip() and len(x.strip()) < 30})

    (OUT / "index.html").write_text(home_page(recipes, len(by_card), chips, people), encoding="utf-8")
    for r in recipes:
        d = OUT / "r" / r["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(recipe_page(r, by_slug, by_card), encoding="utf-8")
    (OUT / "404.html").write_text(not_found_page(), encoding="utf-8")

    today = date.today().isoformat()
    urls = [f"{SITE_URL}/"] + [f"{SITE_URL}/r/{r['slug']}/" for r in recipes]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")

    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
    print(f"Built site/ with {len(recipes)} recipe pages and {len(used)} card images ({size:.0f} MB).")


if __name__ == "__main__":
    main()
