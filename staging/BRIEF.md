# Transcription brief: Grammie's Recipes

You are transcribing scanned family recipe cards into plain-text recipe files. A person
will check every one against the scan in a side-by-side review screen, so accuracy and
honesty about uncertainty matter more than polish.

Project folder: `/Users/clark/Downloads/Source/Grammie's Recipes`

## Inputs

- `web-images/NNNN-a.jpg`, `web-images/NNNN-b.jpg`: two sides of numbered card NNNN (about 2000px wide).
  Some cards have only one side scanned. `-a`/`-b` is just scan order: `-b` is *usually*
  the front (the side with the title), but not always. Decide from the content.
- `web-images/loose-NN.jpg`: loose single scans. Two loose scans may be the same recipe or the
  two sides of one item; say so if you see it.
- Full-resolution originals for zooming into hard handwriting or tiny print:
  `Grammie's Recipes_NNNN_a.jpg` (and `_b`), and `Scanned_20261121-1348-NN.jpg` for loose-NN.
  Crop them with ImageMagick into your own temp directory, for example:
  `magick "<original>" -crop 1600x1000+800+400 +repage /tmp/<you>/crop.jpg` (also `-rotate 90|180|270`).
  Never modify, move, or delete any original or anything in `web-images/`.
- Examples of the finished format (read these first):
  `recipes/frosted-salad.md` (typed card, recipe continues on back, sub-recipe),
  `recipes/granola-bars.md` + `recipes/holiday-raisin-muffins.md` (two recipes on one card),
  `recipes/quiche.md` (handwriting with later notes in another ink, uncertain readings),
  `recipes/coconut-crust.md` (low confidence, two copies of one recipe),
  and `cards.json` (the card list format).

## Output

Write ONLY inside `staging/batch-N/` (N = your batch number):

1. `staging/batch-N/recipes/<slug>.md`: one file per recipe. The slug is lowercase-with-hyphens from
   the title (`cherry-nut-cookies`). If your batch has two recipes with the same title, make the
   slug unique (`chocolate-cake-0042`).
2. `staging/batch-N/cards.json`: a JSON array with one entry per card in your batch, in the same
   shape as the top-level `cards.json`:
   ```json
   {
     "id": "0042",
     "images": [
       { "file": "0042-b.jpg", "label": "Front" },
       { "file": "0042-a.jpg", "label": "Back", "rotate": 180, "note": "Blank" }
     ],
     "recipes": ["chocolate-cake-0042"],
     "status": "needs-review"
   }
   ```
   - List the images in reading order (front first). `label` is "Front"/"Back" for cards and "Scan" for a
     single loose scan; use something clearer if it fits better ("Clipping", "Page 2").
   - `rotate` (90, 180 or 270, clockwise) only when that side has to be turned to read upright.
   - Image `note` only for a side worth noting ("Blank", "Advertisement on back", "Crossed-out list, not a recipe").
   - If a card has no recipe at all, use `"recipes": []` and add a card-level `"note"` saying what it is
     and suggesting whether to leave it off the site.
   - Status is always `"needs-review"`.
3. `staging/batch-N/REPORT.md`: short. Anything a human should know: cards that seem to continue on
   another card, possible duplicates, things you couldn't read at all, judgment calls you made.

## Recipe file format

```
---
title: Cherry Nut Cookies
card: 0006
tags: [cookies, dessert, cherry, nuts, brown sugar, baking]
confidence: high
---

## Ingredients
- 1 cup brown sugar
...

### Topping          <- optional sub-recipe or component; same heading in Directions
- ...

## Directions
1. ...

## Notes
- ...
```

- `title`: the card's own title, with spelling fixed. If the card has no title, make a plain descriptive
  one and say so in Notes. If a word of the title is uncertain, wrap the title in double quotes:
  `title: "[Holder?] Peanut Brittle"`.
- `card`: the card id the recipe comes from (if it spans two cards, the first one, and mention the other in Notes).
- `tags`: lowercase. This is the search index, so be generous and useful. Include the dish type
  (cake, cookies, pie, candy, salad, soup, casserole, bread, main dish, side dish, dessert, drink, sauce…),
  every notable ingredient (chicken, beef, cheese, chocolate, flour, apple, pineapple…),
  and occasion words written on the card (christmas, halloween). Usually 5–12 tags.
- `confidence`: `high` (clean type or print, or very clear handwriting), `medium` (handwriting with a
  few guesses), `low` (hard cursive, faded, or lots of guesses).

### Transcription rules

- **Transcribe what the card says. Never invent amounts, steps, or ingredients.** If the card gives no
  amounts, list ingredients without amounts. If the method is missing or partial, keep it partial and say
  so in Notes.
- **Mark every uncertain reading inline** with square brackets and a question mark: `[30?]`, `[Holder?]`,
  `[1/2?] tsp. salt`. One bracket per uncertain word or number. Do not use square brackets for anything else.
- **Fix spelling and typos** in the readable text (sirup → syrup, Disslove → Dissolve), and list every fix
  on one line in Notes: `- Spelling fixed: a → b, c → d.` Keep old-fashioned but valid wording
  (oleo, sweet milk, soda, No. 303 can). Abbreviations may stay as written (Tbsp., tsp., c.).
- Ingredients one per line. Fractions as `1/2`, `1 1/2`. Temperatures as `350°`.
- Directions as numbered steps. Split long typed paragraphs into sensible steps without rewording much.
  If the card only lists ingredients plus a one-liner, one step is fine.
- **Notes section** (always include it) records the "receipt" details: typed / handwritten / printed
  clipping / brand card (and which company); ink color when there's more than one; handwritten additions
  in the margins or in another ink (put these in Notes rather than merging them into the ingredients,
  unless they're clearly part of the original line); dates, names ("From the kitchen of …"), yields, serving
  sizes, oven sizes, cooking tips; that the recipe continues on the back or upside down; what's on the other
  side if it isn't part of the recipe.
- Several recipes on one card → one file each, all listed in that card's `recipes` array.
- One recipe spread across both sides → one file. A sub-recipe the main recipe refers to
  ("topping on back", "glacé syrup on back") goes in the same file as a `###` component.
  Two unrelated recipes on the two sides → two files.
- Printed clippings and brand recipe cards: transcribe the recipe(s) fully. Skip ads, coupons, and
  unrelated articles; mention them in the image note. A clipping holding several recipes → one file each.
- Not a recipe at all (shopping lists, address labels, certificates, blank pages, steak-cooking charts):
  no recipe file; describe it in the card or image `note`. Cooking tips/charts can be a card note
  instead of a recipe ("Omaha Steaks cooking chart; suggest leaving off the site").

## Working method

Look at both sides of every card at full size (rotate copies as needed; don't guess at sideways or
upside-down text). Zoom into the original for anything faint, tiny, or cursive before deciding something
is uncertain. Work card by card and write each file as you go. When you finish, reply with a few lines:
how many cards and recipes, how many are low confidence, and anything from your REPORT.md worth
flagging. Don't paste the recipes into your reply.
