#!/usr/bin/env python3
"""Targeted supplemental arXiv harvest for taxonomy-v2 gap categories.

The original seven seed queries under-covered three directions that the
revised taxonomy makes first-class: self-evaluation methods, test-time
training, and zero-data self-play ("Agent0" line). This script queries
the arXiv API for those directions (2024+), dedupes against corpus_v2,
tags category/subcategory, and appends rows with source=supplement.

Usage: python3 scripts/supplement_harvest.py
"""

import csv
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "artifacts" / "corpus_v2.csv"
NS = {"atom": "http://www.w3.org/2005/Atom"}
PER_QUERY = 50

QUERIES = [
    # --- self-evaluation ---
    ('all:"LLM-as-a-judge"', "evaluation", ""),
    ('all:"LLM as a judge"', "evaluation", ""),
    ('all:"process reward model"', "evaluation", ""),
    ('all:"generative verifier"', "evaluation", ""),
    ('all:"reward model" AND all:"overoptimization"', "evaluation", ""),
    ('all:"reward hacking"', "evaluation", ""),
    ('all:"self-verification" AND cat:cs.CL', "evaluation", ""),
    ('all:"meta-evaluation" AND all:"judge"', "evaluation", ""),
    ('all:"rubric" AND all:"LLM" AND all:evaluation', "evaluation", ""),
    ('all:"reward model" AND all:benchmark AND cat:cs.CL', "evaluation", ""),
    # --- test-time training ---
    ('all:"test-time training" AND cat:cs.CL', "deployment", "ttt"),
    ('all:"test-time training" AND all:"language model"', "deployment", "ttt"),
    ('all:"test-time adaptation" AND all:"large language model"', "deployment", "ttt"),
    # --- zero-data self-play / Agent0 line ---
    ('all:"self-play" AND all:"zero data"', "training", ""),
    ('all:"proposer" AND all:"solver" AND all:"self-play"', "training", ""),
    ('all:"absolute zero" AND all:reasoning', "training", ""),
    ('all:"self-evolving" AND all:"zero data"', "training", ""),
]

RELEVANT = re.compile(
    r"\b(LLM|language model|large language|agent|reasoning|VLM|multimodal|"
    r"foundation model|GPT|transformer)\b", re.I)

def fetch(query, n=PER_QUERY):
    url = ("http://export.arxiv.org/api/query?search_query=" +
           urllib.parse.quote(query) +
           f"&start=0&max_results={n}&sortBy=submittedDate&sortOrder=descending")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return ET.fromstring(r.read())
        except Exception as e:
            if attempt == 2:
                print(f"  FAILED {query}: {e}")
                return None
            time.sleep(4)

def main():
    rows = list(csv.DictReader(open(CORPUS)))
    seen = {re.sub(r"v\d+$", "", r["arxiv_id"].strip()) for r in rows}
    fields = list(rows[0].keys())

    new_rows, per_query = [], {}
    for query, cat, sub in QUERIES:
        root = fetch(query)
        time.sleep(3)  # arXiv API politeness
        if root is None:
            continue
        added = 0
        for entry in root.findall("atom:entry", NS):
            aid = re.sub(r"v\d+$", "", entry.find("atom:id", NS).text.split("/abs/")[-1])
            if aid in seen:
                continue
            pub = entry.find("atom:published", NS).text  # e.g. 2025-03-01T...
            year = int(pub[:4])
            if year < 2024:
                continue
            title = re.sub(r"\s+", " ", entry.find("atom:title", NS).text.strip())
            summary = re.sub(r"\s+", " ", entry.find("atom:summary", NS).text.strip())
            if not RELEVANT.search(title + " " + summary[:400]):
                continue
            cats = [c.get("term") for c in entry.findall("atom:category", NS)]
            if not any(c.startswith("cs.") or c.startswith("stat.ML") for c in cats):
                continue
            seen.add(aid)
            new_rows.append({
                **{k: "" for k in fields},
                "arxiv_id": aid, "title": title, "year": str(year),
                "pub_date": pub[:19].replace("T", " "),
                "primary_cat": cats[0] if cats else "",
                "cited_by": "", "venue": "", "cluster": "",
                "url": f"https://arxiv.org/abs/{aid}",
                "summary": summary,
                "theme": "(supplement)", "theme_family": "(supplement)",
                "category": cat, "subcategory": sub, "source": "supplement",
            })
            added += 1
        per_query[query] = added
        print(f"  +{added:3d}  {query}")

    with open(CORPUS, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writerows(new_rows)

    from collections import Counter
    c = Counter((r["category"], r["subcategory"]) for r in new_rows)
    print(f"\nappended {len(new_rows)} supplement rows to {CORPUS}")
    for (cat, sub), n in sorted(c.items()):
        print(f"  {cat:12s} {sub:6s} {n}")
    total = len(rows) + len(new_rows)
    print(f"corpus total: {total}")

if __name__ == "__main__":
    main()
