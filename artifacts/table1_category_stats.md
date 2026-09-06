# Table 1 — per-category corpus statistics

Verbatim stdout of `python3 draft/scripts/build_figures_v2.py` (regenerate to reproduce).

```text
1250 corpus rows

### Table 1 (markdown)

| Category | Sub-threads | Papers | of which supplement | % posted 2026 |
|---|---|---:|---:|---:|
| Deployment-time self-evolution | output refinement · test-time training · harness/skill evolution | 393 | 81 | 74% |
| Training-time self-iteration | self-reward RL · CoT self-training · self-distillation · self-play (incl. zero-data) · embodied | 340 | 14 | 69% |
| Self-evaluation | judges · process/reward models · verifiers · rubrics · meta-evaluation | 318 | 284 | 82% |
| Auto Research | AI scientists · evolutionary program discovery | 139 | 0 | 76% |
| Foundations, limits & safety | theory · limits · safety | 60 | 0 | 57% |

deployment subcats: {'refine': 193, 'harness': 113, 'ttt': 87}
omitted partial quarter from Figure 2: 2026Q3 (n=14)
```
