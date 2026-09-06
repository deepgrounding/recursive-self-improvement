#!/usr/bin/env python3
"""Build the Overleaf/arXiv LaTeX project from main.md.

Pipeline: pandoc (--natbib) -> post-process main.tex (heading levels,
author block, abstract env, figure captions, bibliography hookup) ->
clean references.bib for plain bibtex + pdfLaTeX -> write latex/.

Usage: python3 scripts/build_latex.py   (run from draft/)
Output: latex/{main.tex, references.bib, figures/*.png}
"""

import re
import subprocess
import shutil
from pathlib import Path

DRAFT = Path(__file__).resolve().parents[1]
LATEX = DRAFT / "latex"
(LATEX / "figures").mkdir(parents=True, exist_ok=True)

AUTHOR_BLOCK = r"""\author{Mingguang Chen\textsuperscript{1,$*$} \quad Licheng Wang\textsuperscript{2} \quad Bo Qu\textsuperscript{3}\\[6pt]
{\small \textsuperscript{1}University of California, Riverside (UCR) \quad
\textsuperscript{2}AlphaAvatar \quad
\textsuperscript{3}Illinois Institute of Technology (IIT)}\\[2pt]
{\small \textsuperscript{$*$}Corresponding authors. Email: \href{mailto:mchen041@ucr.edu}{mchen041@ucr.edu}}}"""

# ---------- 1. pandoc ----------
subprocess.run([
    "pandoc", str(DRAFT / "main.md"), "-s", "--natbib",
    "--bibliography", str(DRAFT / "combined.bib"),
    "-V", "documentclass=article", "-V", "fontsize=11pt",
    "-V", "geometry:margin=1in", "-V", "colorlinks=true",
    "-V", "biblio-style=unsrtnat", "-V", "natbiboptions=numbers",
    "-o", str(LATEX / "main.tex"),
], check=True)

tex = (LATEX / "main.tex").read_text()

# ---------- 2. heading levels: md '##' landed one level too deep ----------
tex = tex.replace(r"\subsubsection{", r"\XSUBSECTIONX{")
tex = tex.replace(r"\subsection{", r"\section{")
tex = tex.replace(r"\XSUBSECTIONX{", r"\subsection{")

# ---------- 3. author / date ----------
tex = re.sub(r"\\author\{[^{}]*\}", lambda m: AUTHOR_BLOCK, tex, count=1)
tex = re.sub(r"\\date\{[^}]*\}", r"\\date{July 2026}", tex)

# ---------- 4. Abstract section -> abstract environment ----------
m = re.search(
    r"\\section\{Abstract\}\\label\{abstract\}\n\n(.*?)\n\n(?=\\section)",
    tex, flags=re.S)
if m:
    abstract_text = m.group(1)
    tex = tex[:m.start()] + tex[m.end():]
    tex = tex.replace(
        r"\maketitle",
        "\\maketitle\n\n\\begin{abstract}\n" + abstract_text + "\n\\end{abstract}",
        1)

# ---------- 5. figure captions: keep the manual 'Figure N:' text, drop
# LaTeX's own auto-number (md figure order is 3,1,2 so auto-numbering
# would contradict the in-text references) ----------
tex = tex.replace(
    r"\usepackage{longtable,booktabs,array}",
    "\\usepackage{longtable,booktabs,array}\n\\usepackage{caption}")
tex = re.sub(r"\\caption\{(Figure \d+:)", r"\\caption*{\1", tex)

# ---------- 6. References: drop the markdown section + provenance note,
# keep natbib's \bibliography pointing at the cleaned local bib ----------
tex = re.sub(
    r"\\section\{References\}\\label\{references\}\n\n\\emph\{.*?\}\n\n",
    "", tex, flags=re.S)
tex = re.sub(r"\\bibliography\{[^}]*\}", r"\\bibliography{references}", tex)

(LATEX / "main.tex").write_text(tex)

# ---------- 7. clean bib for plain bibtex + pdfLaTeX ----------
bib = (DRAFT / "combined.bib").read_text()
# strip the '% theme:' trailing comments (bibtex chokes on them) and the
# now-empty note fields they annotated
bib = re.sub(r"\n  note = \{\},  % theme: [^\n]*", "", bib)
# escape characters missing from pdfLaTeX's standard utf8 support
for src, dst in {
    "‐": "-",            # unicode hyphen
    "­": "",             # soft hyphen
    "ũ": r"\~{u}",       # u with tilde
    "ấ": r"\'{\^{a}}",   # a circumflex + acute
    "ễ": r"\~{\^{e}}",   # e circumflex + tilde
    "ț": r"\c{t}",       # t with comma below (cedilla approximation)
    "Ț": r"\c{T}",
}.items():
    bib = bib.replace(src, dst)
(LATEX / "references.bib").write_text(bib)

# ---------- 8. figures ----------
for png in (DRAFT / "figures").glob("*.png"):
    shutil.copy2(png, LATEX / "figures" / png.name)

print(f"wrote {LATEX}/main.tex, references.bib, figures/")
print("compile check:  cd latex && tectonic main.tex   (or upload to Overleaf)")
