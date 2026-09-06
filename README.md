# Recursive Self-Improvement in AI

Corpus, classification, figure/bibliography code, and manuscript source for:

> Mingguang Chen, Licheng Wang, Bo Qu. **"Recursive Self-Improvement in AI:
> From Bounded Self-Refinement to Autonomous Research Loops."** 2026.
> arXiv:[2607.07663](https://arxiv.org/abs/2607.07663)

**One-line summary.** "Self-improvement" names four different things. We survey
1,250 arXiv papers (2024–2026) and organize them by *what the system improves*
— its deployment-time behavior, its policy through training, its evaluator, or
the research process itself — crossed with the *degree of loop closure*
(human-in / human-on / closed). Self-evaluation gets a category of its own,
because every improvement loop is a claim that some signal can substitute for
human judgment.

> **Repository relocation.** The paper's Data availability statement cites
> `github.com/bamboodrift/recursive_self_improvement`, which was never made
> public. This repository supersedes that link and is the canonical release;
> the citation will be corrected in the next arXiv version.

## Layout

```text
artifacts/
  corpus_v2.csv                  # THE corpus: 1,250 papers with taxonomy assignments
  self_improvement_corpus.csv    # frozen seed snapshot (871 papers) w/ the earlier
                                 #   unsupervised 13-topic clustering; input to reclassify
  theme_summary.csv              # per-theme counts from the seed harvest
  table1_category_stats.md       # per-category statistics behind Table 1

draft/
  main.md            # manuscript source (matches arXiv v1)
  references.bib     # 1,250 generated entries — do not hand-edit, see below
  anchors.bib        # ~24 hand-curated seminal works outside the harvest window
  pdf-header.tex     # disables LaTeX auto figure numbers (captions carry manual prefixes)
  figures/           # Figures 1-6 as they appear in the paper
  scripts/
    reclassify_corpus.py   # seed csv -> corpus_v2.csv (category/subcategory assignment)
    supplement_harvest.py  # appends the 379-paper targeted supplement
    build_bib.py           # corpus_v2.csv -> references.bib (OpenAlex + arXiv API)
    build_figures_v2.py    # -> Figures 2 and 6, prints Table 1
    build_latex.py         # main.md -> LaTeX project (Overleaf/arXiv)
```

## The taxonomy

The `category` column of `corpus_v2.csv` uses these short codes:

| code | section | category |
|---|---|---|
| `deployment` | §3 | Deployment-time self-evolution (`subcategory`: `refine` / `ttt` / `harness`) |
| `training` | §4 | Training-time self-iteration |
| `evaluation` | §5 | Self-evaluation |
| `research` | §6 | Auto Research |
| `foundations` | §7 | Foundations, limits & safety |

Classification is theme→category defaults + keyword rules + an explicit
per-paper `OVERRIDES` dict, all in `reclassify_corpus.py`; the rules moved 89
seed papers off their thread defaults and 3 further misfires were corrected by
override. Corrections belong in `OVERRIDES`, not in hand-edits to the CSV.

`corpus_v2.csv` columns: `arxiv_id, title, year, pub_date, primary_cat,
cited_by, venue, cluster, url, summary, theme, theme_family, category,
subcategory, source`. `cited_by` is empty for supplement rows and near-zero for
most 2026 papers — a stated limitation (§2.3), not missing data.

## Reproducing

Python 3.11+ with `numpy` and `matplotlib`. **Order matters:**

```bash
python3 draft/scripts/reclassify_corpus.py    # seed csv -> corpus_v2.csv (SEED ROWS ONLY)
python3 draft/scripts/supplement_harvest.py   # appends the supplement rows back
python3 draft/scripts/build_bib.py            # -> draft/references.bib
python3 draft/scripts/build_figures_v2.py     # -> Figures 2 and 6, prints Table 1
```

`reclassify_corpus.py` rewrites `corpus_v2.csv` from the seed snapshot and
therefore **drops the 379 supplement rows unless `supplement_harvest.py` is
rerun after it**. `supplement_harvest.py` dedupes on arXiv ID, so rerunning is
safe — but it queries arXiv live, so a rerun today will pull papers posted
since the July 2026 freeze and change the counts quoted in the paper. The
frozen `corpus_v2.csv` in this repository is what the paper reports.

`build_bib.py` reads an optional `OPENALEX_API_KEY` from the environment (or a
local, uncommitted `.env`); without one it uses OpenAlex's anonymous pool,
which is slower but works. Note that it derives citation keys from first-author
surname + year + first title word, so regenerating after OpenAlex improves its
author metadata can rename keys — check `main.md`'s citations against the
regenerated bib before compiling.

Figure 6 (growth timeline) is built from seed rows only (`source == "seed"`),
because the supplemental harvest is recency-biased by construction (§2.3).
Figures 1 and 3–5 are hand-designed/generated concept diagrams with no build
script; they are included here as the PNGs used in the paper.

Building the manuscript:

```bash
cd draft
cat references.bib anchors.bib > combined.bib
pandoc main.md --citeproc --bibliography=combined.bib --pdf-engine=tectonic \
  -H pdf-header.tex -V geometry:margin=1in -V fontsize=11pt -V colorlinks=true -o survey.pdf
```

## License

- **Code** (`draft/scripts/*.py`) — MIT, see `LICENSE`.
- **Manuscript, figures, and corpus data** (`draft/main.md`, `draft/figures/`,
  `artifacts/`) — CC BY 4.0, see `LICENSE-CC-BY`. Paper metadata in the corpus
  (titles, abstracts, dates) is derived from arXiv and OpenAlex and remains
  subject to the terms of those sources.

## Citation

```bibtex
@article{chen2026rsisurvey,
  title   = {Recursive Self-Improvement in {AI}: From Bounded Self-Refinement to Autonomous Research Loops},
  author  = {Chen, Mingguang and Wang, Licheng and Qu, Bo},
  year    = {2026},
  journal = {arXiv preprint arXiv:2607.07663},
  url     = {https://arxiv.org/abs/2607.07663}
}
```

## Contact

deepgroundingai@gmail.com · [github.com/deepgrounding](https://github.com/deepgrounding)
