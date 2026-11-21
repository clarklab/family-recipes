#!/usr/bin/env python3
"""Compare recipes/ against a backup taken before the notes rewrite.

Fails if anything outside the ## Notes section changed (other than an added `from:` line),
or if any [..?] uncertainty mark outside Notes was lost. Prints a short summary.

    python3 staging/check_notes.py <backup-dir>
"""
import re
import sys
from pathlib import Path

RECIPES = Path(__file__).resolve().parent.parent / "recipes"
backup = Path(sys.argv[1])


def split(text):
    m = re.search(r"^## Notes\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    notes = m.group(1).strip() if m else ""
    rest = text[: m.start()] + text[m.end():] if m else text
    rest = "\n".join(l for l in rest.splitlines() if not l.startswith("from:"))
    return re.sub(r"\n{2,}", "\n\n", rest).strip(), notes


problems, removed, before_lines, after_lines, banned = [], 0, 0, 0, []
BANNED = re.compile(r"spelling|typo|correction tape|overwrit|written over|cut off|scan|not given|no method|missing", re.I)
for old in sorted(backup.glob("*.md")):
    new = RECIPES / old.name
    if not new.exists():
        problems.append(f"{old.name}: file disappeared")
        continue
    o_rest, o_notes = split(old.read_text())
    n_text = new.read_text()
    n_rest, n_notes = split(n_text)
    if o_rest != n_rest:
        problems.append(f"{old.name}: changed outside Notes")
    if o_notes and not n_notes:
        removed += 1
    before_lines += o_notes.count("\n- ") + (1 if o_notes.startswith("- ") else 0)
    after_lines += n_notes.count("\n- ") + (1 if n_notes.startswith("- ") else 0)
    for line in n_notes.splitlines():
        if BANNED.search(line):
            banned.append(f"{old.name}: {line[:140]}")

print(f"Note lines: {before_lines} -> {after_lines}; Notes sections removed entirely: {removed}")
for b in banned:
    print("check wording:", b)
for p in problems:
    print("PROBLEM:", p)
