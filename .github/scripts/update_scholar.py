#!/usr/bin/env python3
"""Fetch Google Scholar citation metrics and save them to assets/data/scholar.json.

Besides the profile totals, it saves each paper's title, year and "cited by"
count under "papers", which the website uses to label its publication list.

Tries the public profile page first. If Google blocks the request and a
SERPAPI_KEY secret is set, falls back to SerpAPI. If both fail, the script
exits with an error and leaves the existing JSON file untouched, so the site
keeps showing the last good numbers.
"""
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

SCHOLAR_ID = os.environ.get("SCHOLAR_ID", "pQL-hZsAAAAJ")
OUT = os.environ.get("SCHOLAR_OUT", "assets/data/scholar.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse_profile(html):
    """The stats table holds six cells: citations, h-index, i10-index, each as (all, recent)."""
    cells = re.findall(r'<td class="gsc_rsb_std">(\d+)</td>', html)
    if len(cells) < 6:
        raise ValueError("stats table not found (page blocked or layout changed)")
    return {"citations": int(cells[0]), "h_index": int(cells[2]), "i10_index": int(cells[4])}


def count_rows(html):
    """Each article on the profile is one table row."""
    return len(re.findall(r'<tr class="gsc_a_tr"', html))


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text or "")).strip()


def parse_papers(html):
    """Title, citation count and year for every article row on a profile page."""
    papers = []
    for row in re.findall(r'<tr class="gsc_a_tr".*?</tr>', html, re.S):
        title = re.search(r'class="gsc_a_at"[^>]*>(.*?)</a>', row, re.S)
        cited = re.search(r'class="gsc_a_ac[^"]*"[^>]*>(\d*)</a>', row)
        year = re.search(r'class="gsc_a_h gsc_a_hc[^"]*"[^>]*>(\d{4})<', row)
        if title:
            papers.append({"title": clean(title.group(1)),
                           "cited_by": int(cited.group(1)) if cited and cited.group(1) else 0,
                           "year": int(year.group(1)) if year else None})
    return papers


def from_scholar():
    base = f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en&pagesize=100"
    html = get(base + "&cstart=0")
    stats = parse_profile(html)
    papers, start = parse_papers(html), 0
    n = count_rows(html)
    while n >= 100 and start < 900:
        start += 100
        page = get(f"{base}&cstart={start}")
        n = count_rows(page)
        papers += parse_papers(page)
    stats["articles"] = len(papers) or None
    stats["papers"] = papers
    return stats


def from_serpapi(key):
    q = urllib.parse.urlencode({"engine": "google_scholar_author", "author_id": SCHOLAR_ID,
                                "hl": "en", "num": 100, "api_key": key})
    data = json.loads(get("https://serpapi.com/search.json?" + q))
    out = {}
    for row in data.get("cited_by", {}).get("table", []):
        for k, v in row.items():
            name = {"citations": "citations", "h_index": "h_index", "i10_index": "i10_index"}.get(k)
            if name and isinstance(v, dict) and "all" in v:
                out[name] = int(v["all"])
    if "citations" not in out:
        raise ValueError("SerpAPI response had no citation table")
    papers = []
    for a in data.get("articles", []):
        cited = (a.get("cited_by") or {}).get("value")
        year = str(a.get("year") or "")
        papers.append({"title": clean(a.get("title")),
                       "cited_by": int(cited) if cited else 0,
                       "year": int(year) if year.isdigit() else None})
    n = len(papers)
    return {"citations": out["citations"], "h_index": out.get("h_index"), "i10_index": out.get("i10_index"),
            "articles": n if 0 < n < 100 else None, "papers": papers}


def main():
    errors = []
    sources = [("scholar", from_scholar)]
    key = os.environ.get("SERPAPI_KEY", "").strip()
    if key:
        sources.append(("serpapi", lambda: from_serpapi(key)))
    for name, fn in sources:
        try:
            stats = fn()
        except Exception as e:  # network block, captcha, layout change
            errors.append(f"{name}: {e}")
            continue
        stats["updated"] = datetime.date.today().isoformat()
        stats["source"] = name
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
            f.write("\n")
        print("saved", {k: v for k, v in stats.items() if k != "papers"})
        for p in stats.get("papers", []):
            print(f"  paper: {p['cited_by']:>4}  {p['year']}  {p['title']}")
        return 0
    print("Could not update Scholar metrics; keeping the existing file.", *errors, sep="\n  ", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
