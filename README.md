# Grammie's Recipes

The family recipe box, typed up from the original cards: 177 recipes from 155 cards, each one
linked to photos of the card it came from.

## Look at the recipes

Open `site/index.html` in a browser, or serve the folder:

```bash
python3 -m http.server 8766 --directory site
```

then go to http://localhost:8766. Search by ingredient, dish, or name ("chicken", "cake",
"pecans", "Viki"), browse A to Z, and tap a card photo to see the original up close.

## What's here

| Path | What it is |
| --- | --- |
| `recipes/` | One plain-text file per recipe (title, tags, ingredients, directions, notes). Words that were hard to read on the card are marked like `[30?]`. |
| `cards.json` | Every scanned card: its image files, which way to turn them, and which recipes are on it. |
| `web-images/` | Web-sized copies of every scan, with personal details (phone numbers, addresses, receipts, letters) blurred. |
| `site-src/` | The website's page, styles, and script. |
| `site/` | The built website, ready to open or host anywhere. |
| `build_site.py` | Rebuilds `site/` from the recipes and cards. |
| `review/` | The side-by-side screen used to check transcriptions against the cards. |
| `staging/` | The instructions and scripts used to transcribe the cards. |

## Fix a recipe

Edit its file in `recipes/`, then rebuild:

```bash
python3 build_site.py
```

To check recipes against their cards side by side, run `python3 review/server.py` and open
http://localhost:8765.

The original full-resolution scans aren't in this repository: they're large and include
unblurred personal details.
