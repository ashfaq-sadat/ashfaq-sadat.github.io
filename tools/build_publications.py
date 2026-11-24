#!/usr/bin/env python3
"""Write the publication list into index.html and publications.html.

The list lives in assets/data/publications.json. Edit that file (add a paper,
fix a title), then run:

    python3 tools/build_publications.py

It replaces everything between the PUBLICATIONS:START and PUBLICATIONS:END
markers in both pages, and updates the "See all N publications" count.
The pages stay plain HTML, so search engines see the full list.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "assets" / "data" / "publications.json"
PAGES = [ROOT / "index.html", ROOT / "publications.html"]
START, END = "<!-- PUBLICATIONS:START -->", "<!-- PUBLICATIONS:END -->"


def item_html(p, indent="          "):
    title = p["title_html"]
    if p.get("url"):
        title_el = (f'<a class="ptitle" href="{html.escape(p["url"])}" rel="noopener" target="_blank">'
                    f'{title}</a>')
    else:
        title_el = f'<span class="ptitle">{title}</span>'
    lines = [
        f'<li data-t="{" ".join(p["topics"])}" data-year="{p["year"]}"',
        f'  data-cite="{html.escape(p["citation"], quote=True)}">',
        f'  <span class="year">{p["year"]}</span>',
        '  <div>',
        f'    {title_el}',
        f'    <span class="authors">{p["authors_html"]}</span>',
        f'    <span class="venue">{p["venue_html"]}</span>',
        f'    <span class="meta"><span class="tag">{html.escape(p["type"])}</span>',
        '      <button class="copy" type="button">Copy citation</button></span>',
        '  </div>',
        '</li>',
    ]
    return "\n".join(indent + line for line in lines)


def main():
    pubs = json.loads(DATA.read_text(encoding="utf-8"))
    # Newest first; the pages re-sort by citations on request
    pubs.sort(key=lambda p: -p["year"])
    block = START + "\n" + "\n".join(item_html(p) for p in pubs) + "\n          " + END
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        if START not in text:
            raise SystemExit(f"{page.name}: markers not found")
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, flags=re.S)
        text = re.sub(r'(<span class="pub-count">)\d+(</span>)', rf"\g<1>{len(pubs)}\2", text)
        page.write_text(text, encoding="utf-8")
        print(f"{page.name}: {len(pubs)} publications")


if __name__ == "__main__":
    main()
