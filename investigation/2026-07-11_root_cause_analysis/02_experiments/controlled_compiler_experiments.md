# Design of Controlled Compiler Experiments
*Objective Validation of Architectural Solutions*

## Task 1 — Architectural Hypotheses

**H1: The Semantic Firewall Hypothesis**
`Semantic` is artificially bottlenecked by strictly gating structural parsing behind `is_outlier`. If `Semantic` evaluates all groups using its internal `universal_body_class` and regex matchers, it can natively recover the missed headers (the "Valley" effect) without any modifications to `Landmarks`.

**H2: The Landmark Math Hypothesis**
The local maximum equation (`curr <= prev` and `curr <= next`) is mathematically too strict for modern layouts. Relaxing the inequality to strictly less than (`curr < prev`) will restore headers that share typography classes with adjacent blocks, though at the risk of increased noise.

**H3: The Geometric Blindness Hypothesis**
`Semantic` promotes `INLINE_BOLD` and `TABLE_VALUE` because the `OUTLIER` boolean strips away physical context. If `Semantic` incorporates geometric bounding boxes to verify isolation, it will perfectly filter the 93 false positives emitted by `Landmarks`.

---

## Task 2 — Experimental Designs

### EXP-03: Disable Semantic Outlier Gate (Tests H1)
*   **Action**: In `semantic.py` `BODY_PARSE`, remove the `if is_outlier:` wrapper around section header and references logic. Allow the parser to evaluate every group against header regexes and the `universal_body_class`.
*   **Target File**: `extractor/semantic.py`
*   **Lines Touched**: ~3 lines (Remove `if is_outlier:`, dedent block).
*   **Rollback**: `git checkout extractor/semantic.py`.

### EXP-04: Relax Landmark Inequality (Tests H2)
*   **Action**: In `landmarks.py`, change the strict local maximum check `curr <= prev` to `curr < prev` to allow plateau peaks (where adjacent headers share identical typography) to emit as OUTLIERs.
*   **Target File**: `extractor/landmarks.py`
*   **Lines Touched**: ~2 lines.
*   **Rollback**: `git checkout extractor/landmarks.py`.

### EXP-05: Semantic Geometric Verification (Tests H3)
*   **Action**: In `semantic.py`, before trusting `is_outlier`, add a single check: `if is_outlier and group.evidence_vector.bounding_box_width < line_width / 3: return PARAGRAPH`. (Simulates geometric inline rejection).
*   **Target File**: `extractor/semantic.py`
*   **Lines Touched**: ~4 lines.
*   **Rollback**: `git checkout extractor/semantic.py`.

---

## Task 3 — Objective Metrics

Every experiment will be measured deterministically against the EXP-02 baseline using the following metrics:

*   **Header Recall**: (True Headers Detected / Expected Headers) $\rightarrow$ Baseline: 56.0% (14/25).
*   **Header Precision**: (True Headers / Total Emitted Headers) $\rightarrow$ Baseline: 15.6%.
*   **False Positive Rate**: Total non-structural `OUTLIER`s erroneously admitted into the AST as structural nodes. $\rightarrow$ Baseline: 93.
*   **Structural Contamination Ratio**: Ratio of False Positives to True Positives. $\rightarrow$ Baseline: ~1.6 : 1.
*   **Missed Candidates**: Total valid headers rejected. $\rightarrow$ Baseline: 8.

---

## Task 4 — Evaluation Criteria

### EXP-03 (Semantic Firewall)
*   **Success**: Header Recall reaches 100% (Missed Candidates = 0) with zero increase in False Positive Rate.
*   **Failure**: False Positive Rate spikes because `is_outlier` was secretly protecting the AST from vast amounts of noise.
*   **Regression**: AST Hierarchy fails to build or throws recursion errors.

### EXP-04 (Landmark Math)
*   **Success**: Header Recall increases by recovering the 8 missed Spanner headers, without Structural Contamination exceeding 3:1.
*   **Failure**: Header Recall remains unchanged, or False Positives increase by >50%.
*   **Regression**: Existing True Positive boundaries (`TITLE`, `ABSTRACT`) are suddenly rejected.

### EXP-05 (Geometric Verification)
*   **Success**: False Positive Rate drops by >80% (eliminating `INLINE_BOLD` and `TABLE_VALUE`), significantly increasing Header Precision.
*   **Failure**: False Positive Rate decreases by < 10%.
*   **Regression**: True Positive headers (like short subsection headers) are incorrectly filtered as inline noise.

---

## Task 5 — Experiment Ranking

1.  **EXP-03 (Semantic Firewall)**
    *   *Expected Information Gain*: Maximum. It conclusively proves whether `Landmarks` is actually a necessary architectural bottleneck for `Semantic`, or if `Semantic` can operate autonomously.
    *   *Engineering Cost*: Minimal (delete 1 line, dedent block).
    *   *Regression Risk*: High, but instantly visible via AST output.
2.  **EXP-05 (Geometric Verification)**
    *   *Expected Information Gain*: High. It answers whether the architecture's decision to strip geometry at the Landmark stage is the root cause of AST contamination.
    *   *Engineering Cost*: Low.
    *   *Regression Risk*: Medium (could accidentally filter valid short headers).
3.  **EXP-04 (Landmark Math)**
    *   *Expected Information Gain*: Medium. Tweaking the math is highly likely to just shift the noise threshold rather than solve the fundamental "Valley" problem.
    *   *Engineering Cost*: Minimal.
    *   *Regression Risk*: Low (only impacts Landmark boolean emission).

---

## Task 6 — Roadmap

The roadmap maximizes knowledge gained by isolating the variables systematically. We must first determine if Semantic *needs* the Landmark gate (EXP-03). If it does, we must determine if Semantic needs richer geometric data from it (EXP-05). Only if both fail do we resort to tweaking the compiler math (EXP-04).

**Phase 1: EXP-03 (Disable Semantic Outlier Gate)**
*Goal*: Determine if `Semantic` is capable of parsing the document without the lossy `is_outlier` boolean acting as a firewall.

↓

**Phase 2: EXP-05 (Semantic Geometric Verification)**
*Goal*: If Phase 1 proves `is_outlier` is necessary, determine if providing `Semantic` with geometric bounds eliminates the 93 false positives (inline bold/tables).

↓

**Phase 3: EXP-04 (Relax Landmark Inequality)**
*Goal*: If Phase 1 and 2 fail, attempt to mathematically patch the `Landmark` local maximum equation to recover the 8 missed headers.
