#!/usr/bin/env python3
"""Re-classify the 871-paper corpus into the paper's revised taxonomy.

Axis-1 categories (v2, per collaborator feedback):
  deployment  - Deployment-time self-evolution (output refinement,
                test-time training, harness/agent/skill evolution)
  training    - Training-time self-iteration (self-reward RL, CoT
                self-training, OPSD, self-play incl. zero-data, embodied)
  evaluation  - Self-evaluation (the paper's main contribution is the
                evaluator: judges, verifiers, reward models, rubrics,
                meta-evaluation, evaluation benchmarks/analyses)
  research    - Auto Research (AI scientists, evolutionary discovery)
  foundations - Foundations, limits & safety (unchanged meta family)

Rules: theme -> default category, then keyword overrides on
title+abstract, with 'evaluation' extracted from every theme.
Subcategory tags recorded for deployment (refine/ttt/harness).

Output: artifacts/corpus_v2.csv (adds columns: category, subcategory)
plus a console report of counts and reassignment samples.
"""

import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "artifacts" / "self_improvement_corpus.csv"
OUT = ROOT / "artifacts" / "corpus_v2.csv"

THEME_DEFAULT = {
    "LLM Self-Refinement & Self-Improvement": ("deployment", "refine"),
    "Self-Improving Multimodal Vision-Language Models": ("deployment", "refine"),
    "LLM Code Self-Refinement via Feedback": ("deployment", "refine"),
    "Self-Improving LLM Agent Systems": ("deployment", "harness"),
    "Self-Evolving LLM Agents": ("deployment", "harness"),
    "Self-Rewarding RL Self-Improvement": ("training", ""),
    "Self-Training for Chain-of-Thought Reasoning": ("training", ""),
    "On-policy self-distillation for LLM reasoning": ("training", ""),
    "Self-Play for LLM Self-Improvement": ("training", ""),
    "Synthetic Data & Embodied Self-Improvement": ("training", ""),
    "AI Scientist Agents": ("research", ""),
    "LLM-Driven Evolutionary Program Discovery": ("research", ""),
    "Recursive Self-Improvement & Machine Consciousness": ("foundations", ""),
}

# --- keyword rules (checked on title + first 800 chars of abstract) ---

# a paper is 'evaluation' when the evaluator IS the contribution
EVAL_TITLE = re.compile(
    r"\b(LLM[- ]as[- ]a?[- ]?judge|judge|verifier|verification agent|"
    r"reward model|process reward|rubric|meta[- ]evaluat|evaluat\w+ (framework|method|benchmark|criteria)|"
    r"critic model|自?scorer|scoring model|judgment)\b", re.I)
EVAL_STRONG = re.compile(
    r"\b(we (propose|present|introduce)[^.]{0,120}(judge|verifier|reward model|"
    r"evaluation (framework|method|protocol|benchmark)|meta[- ]evaluation|rubric))", re.I)
# but not: papers that merely *use* verifiable rewards to train
EVAL_BLOCK = re.compile(
    r"\b(RLVR|reinforcement learning (with|from) verifiable rewards?|"
    r"self[- ]play fine[- ]tun|policy optimization)\b", re.I)

# test-time training: weight updates at inference
TTT = re.compile(
    r"\b(test[- ]time (training|adaptation|optimization|fine[- ]?tun\w*)|"
    r"query[- ]conditioned (self[- ])?train|online (fine[- ]?tun\w+|adaptation) (at|during) inference|"
    r"TTT)\b", re.I)

# training markers used to move VLM/refinement papers into 'training'
TRAINS = re.compile(
    r"\b(self[- ]train|fine[- ]?tun\w+|DPO|GRPO|PPO|RLHF|RLVR|reinforcement learning|"
    r"post[- ]train\w+|distill\w+|preference optimization|policy optimization|reward[- ]guided train)\b", re.I)
INFERENCE_GUARD = re.compile(
    r"\b(training[- ]free|inference[- ]time|test[- ]time|without (additional |any )?(training|fine[- ]?tuning)|"
    r"frozen (LLM|model|backbone))\b", re.I)

# explicit overrides: papers cited in the manuscript whose section
# placement fixes their category, plus clear rule misfires
OVERRIDES = {
    "2606.00131": ("research", ""),      # AI-PROPELLER (AlphaEvolve application)
    "2408.03314": ("deployment", "refine"),  # Snell test-time compute scaling
    "2605.19156": ("research", ""),      # ResearchArena / How Far Auto-Research
}

def classify(row):
    theme = row["theme"]
    aid = re.sub(r"v\d+$", "", (row.get("arxiv_id") or "").strip())
    if aid in OVERRIDES:
        return OVERRIDES[aid]
    cat, sub = THEME_DEFAULT[theme]
    text = (row["title"] or "") + " || " + (row["summary"] or "")[:800]
    title = row["title"] or ""

    # 1) evaluation extraction (from every technical theme)
    if cat != "foundations":
        if (EVAL_TITLE.search(title) or EVAL_STRONG.search(text)) and not EVAL_BLOCK.search(text):
            return "evaluation", ""

    # 2) test-time training (only meaningful for deployment/training themes)
    if cat in ("deployment", "training") and TTT.search(text):
        return "deployment", "ttt"

    # 3) refinement-theme papers that are actually training-time methods
    if cat == "deployment" and sub == "refine":
        if TRAINS.search(text) and not INFERENCE_GUARD.search(text):
            return "training", ""

    return cat, sub

def main():
    rows = list(csv.DictReader(open(SRC)))
    from collections import Counter
    counts, moved = Counter(), []
    out_rows = []
    for r in rows:
        cat, sub = classify(r)
        default = THEME_DEFAULT[r["theme"]][0]
        if cat != default:
            moved.append((r["theme"][:28], cat, r["title"][:80]))
        counts[(cat, sub)] += 1
        r["category"], r["subcategory"] = cat, sub
        r["source"] = "seed"
        out_rows.append(r)

    fields = list(out_rows[0].keys())
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    print("=== category counts ===")
    cat_totals = Counter()
    for (cat, sub), n in sorted(counts.items()):
        print(f"  {cat:12s} {sub:8s} {n}")
        cat_totals[cat] += n
    print("=== totals ===")
    for cat, n in cat_totals.most_common():
        print(f"  {cat:12s} {n}")
    print(f"\n{len(moved)} papers moved off their theme default; samples:")
    for theme, cat, title in moved[:25]:
        print(f"  [{theme}] -> {cat}: {title}")
    print(f"\nwrote {OUT}")

if __name__ == "__main__":
    main()
