#!/usr/bin/env python3
"""Build references.bib for the RSI survey.

Reads artifacts/self_improvement_corpus.csv, batch-queries OpenAlex
(via the arXiv DOI 10.48550/arXiv.<id>) for authors/venue/DOI, and writes
draft/references.bib. Papers OpenAlex can't resolve fall back to an
arXiv-only @misc entry built from the corpus row itself.

Usage:  python3 build_bib.py            # OPENALEX_API_KEY from env or repo-root .env (optional)
"""

import csv
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "artifacts" / "corpus_v2.csv"
OUT = ROOT / "draft" / "references.bib"
BATCH = 50

def load_api_key():
    """OPENALEX_API_KEY from the environment, or from a local .env (never committed).
    Optional: without it the script falls back to OpenAlex's anonymous pool."""
    key = os.environ.get("OPENALEX_API_KEY")
    if key:
        return key.strip()
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("OPENALEX_API_KEY"):
                return line.split("=", 1)[1].strip()
    return None

ARXIV_BATCH = 20
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}

def fetch_arxiv_authors(arxiv_ids):
    """Fallback for papers OpenAlex hasn't indexed yet (common for <1 month old
    preprints): query the arXiv API directly, which always has author lists."""
    out = {}
    ids = [re.sub(r"v\d+$", "", i.strip()) for i in arxiv_ids]
    for i in range(0, len(ids), ARXIV_BATCH):
        chunk = ids[i:i + ARXIV_BATCH]
        url = ("http://export.arxiv.org/api/query?id_list=" +
               ",".join(chunk) + f"&max_results={len(chunk)}")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    data = r.read()
                break
            except Exception as e:
                if attempt == 2:
                    print(f"  arXiv batch failed: {e}", file=sys.stderr)
                    data = None
                else:
                    time.sleep(3)
        if not data:
            continue
        root = ET.fromstring(data)
        for entry in root.findall("atom:entry", ARXIV_NS):
            id_full = entry.find("atom:id", ARXIV_NS).text
            aid = re.sub(r"v\d+$", "", id_full.split("/abs/")[-1])
            authors = [a.find("atom:name", ARXIV_NS).text
                       for a in entry.findall("atom:author", ARXIV_NS)]
            if authors:
                out[aid] = authors
        time.sleep(1)
    return out

def fetch_batch(dois, api_key):
    filt = "doi:" + "|".join(dois)
    params = {
        "filter": filt,
        "per-page": str(len(dois)),
        "select": "doi,title,publication_year,authorships,primary_location,type,ids",
    }
    if api_key:
        params["api_key"] = api_key
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)["results"]
        except Exception as e:
            if attempt == 2:
                print(f"  batch failed after retries: {e}", file=sys.stderr)
                return []
            time.sleep(2 * (attempt + 1))

def slugify_key(first_author_last, year, title):
    word = re.sub(r"[^a-z0-9]", "", (
        next((w for w in re.findall(r"[A-Za-z0-9']+", title)
              if w.lower() not in {"a", "an", "the", "on", "of", "for",
                                   "and", "to", "in", "towards", "toward",
                                   "with", "via", "from", "what", "why",
                                   "how", "do", "does", "is", "are"}),
             "paper")
    ).lower())
    last = unicodedata.normalize("NFKD", first_author_last)
    last = re.sub(r"[^a-zA-Z]", "", last).lower() or "anon"
    return f"{last}{year}{word}"

def bib_escape(s):
    return (s.replace("\\", r"\\").replace("&", r"\&").replace("%", r"\%")
             .replace("#", r"\#").replace("_", r"\_").replace("$", r"\$"))

def protect_title(t):
    # Protect acronyms / mixed-case tokens from bibtex lowercasing
    return re.sub(r"\b([A-Za-z]*[A-Z][A-Za-z]*[A-Z][A-Za-z]*|[A-Z]{2,})\b",
                  r"{\1}", bib_escape(t))

NON_LATIN = re.compile(r"[Ѐ-ӿͰ-Ͽ一-鿿぀-ヿ가-힯]")

def make_entry(row, work, arxiv_authors=None):
    arxiv_id = row["arxiv_id"].strip()
    title = (work or {}).get("title") or row["title"]
    year = (work or {}).get("publication_year") or row["year"]
    authors = []
    if work:
        for a in work.get("authorships", []):
            name = a.get("author", {}).get("display_name")
            if name:
                authors.append(name)
    # OpenAlex sometimes stores names in native script (Cyrillic, CJK, ...),
    # which Latin Modern can't typeset; prefer arXiv's Latin transliteration
    if (not authors or any(NON_LATIN.search(a) for a in authors)) and arxiv_authors:
        fallback = arxiv_authors.get(re.sub(r"v\d+$", "", arxiv_id), [])
        if fallback:
            authors = fallback
    src = ((work or {}).get("primary_location") or {}).get("source") or {}
    venue = src.get("display_name") or ""
    is_arxiv_only = (not venue) or "arxiv" in venue.lower()

    first_last = authors[0].split()[-1] if authors else "anon"
    key = slugify_key(first_last, year, title)

    lines = []
    if is_arxiv_only:
        lines.append(f"@misc{{{key},")
    else:
        lines.append(f"@article{{{key},")
    lines.append(f"  title = {{{protect_title(title)}}},")
    if authors:
        lines.append(f"  author = {{{bib_escape(' and '.join(authors))}}},")
    lines.append(f"  year = {{{year}}},")
    if not is_arxiv_only:
        lines.append(f"  journal = {{{bib_escape(venue)}}},")
        doi = ((work or {}).get("doi") or "").replace("https://doi.org/", "")
        if doi:
            lines.append(f"  doi = {{{doi}}},")
    lines.append(f"  eprint = {{{arxiv_id}}},")
    lines.append("  archivePrefix = {arXiv},")
    lines.append(f"  url = {{https://arxiv.org/abs/{arxiv_id}}},")
    # provenance comment: theme, for filtering while writing
    lines.append(f"  note = {{}},  % theme: {row['theme']}")
    lines.append("}")
    return key, "\n".join(lines), bool(authors), not is_arxiv_only

def main():
    api_key = load_api_key()
    if not api_key:
        print("warning: no OPENALEX_API_KEY found in .env; using anonymous pool",
              file=sys.stderr)

    with open(CORPUS) as f:
        rows = list(csv.DictReader(f))
    print(f"{len(rows)} corpus rows")

    # strip version suffix (e.g. 2401.02051v2 -> 2401.02051) for DOI form
    def doi_of(r):
        base = re.sub(r"v\d+$", "", r["arxiv_id"].strip())
        return f"10.48550/arXiv.{base}"

    works_by_doi = {}
    dois = [doi_of(r) for r in rows]
    for i in range(0, len(dois), BATCH):
        chunk = dois[i:i + BATCH]
        for w in fetch_batch(chunk, api_key):
            d = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            if d:
                works_by_doi[d] = w
        print(f"  fetched {min(i + BATCH, len(dois))}/{len(dois)} "
              f"(resolved so far: {len(works_by_doi)})")
        time.sleep(0.1)

    # fallback: papers OpenAlex hasn't indexed, indexed without an author
    # list, or indexed with native-script (non-Latin) author names
    def needs_arxiv(w):
        if not w or not w.get("authorships"):
            return True
        return any(NON_LATIN.search(a.get("author", {}).get("display_name") or "")
                   for a in w["authorships"])

    still_missing = [r["arxiv_id"] for r in rows
                      if needs_arxiv(works_by_doi.get(doi_of(r).lower()))]
    print(f"\n{len(still_missing)} rows unresolved/authorless in OpenAlex; "
          f"querying arXiv API directly...")
    arxiv_authors = fetch_arxiv_authors(still_missing) if still_missing else {}
    print(f"  arXiv fallback resolved authors for {len(arxiv_authors)}/{len(still_missing)}")

    entries, seen_keys = [], set()
    n_authors = n_venue = n_resolved = 0
    for r in rows:
        w = works_by_doi.get(doi_of(r).lower())
        if w:
            n_resolved += 1
        key, entry, has_auth, has_venue = make_entry(r, w, arxiv_authors)
        # de-duplicate keys
        k, suffix = key, ord("a")
        while k in seen_keys:
            k = key + chr(suffix)
            suffix += 1
        if k != key:
            entry = entry.replace(f"{{{key},", f"{{{k},", 1)
        seen_keys.add(k)
        entries.append(entry)
        n_authors += has_auth
        n_venue += has_venue

    OUT.write_text(
        f"% Auto-generated from self_improvement_corpus.csv via OpenAlex "
        f"({time.strftime('%Y-%m-%d')})\n"
        f"% {len(entries)} entries; {n_resolved} resolved in OpenAlex; "
        f"{n_authors} with authors; {n_venue} with non-arXiv venue\n\n"
        + "\n\n".join(entries) + "\n")
    print(f"\nwrote {OUT}")
    print(f"resolved in OpenAlex: {n_resolved}/{len(rows)}")
    print(f"with authors:         {n_authors}/{len(rows)}")
    print(f"with published venue: {n_venue}/{len(rows)}")

if __name__ == "__main__":
    main()
