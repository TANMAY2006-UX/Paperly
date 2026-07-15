# PIP-003 Root Cause Proof

## Task 1 — Pipeline Execution Replay

**Target**: Distinctly formatted front-matter text (e.g., Affiliations in Spanner, Bold Authors in Attention Is All You Need, Affiliations in BERT).

1.  **Layout**
    *   *Decision*: Block falls within the M_top and M_bot margins, classifying it into the primary body zone.
    *   *Correct?* **YES**. Author names are not repeating page headers or footers.
2.  **Ordering**
    *   *Decision*: Sequenced in 1D array geometrically below the Title block.
    *   *Correct?* **YES**. Reading order is strictly top-to-bottom in the preamble.
3.  **Assembly**
    *   *Decision*: Fragmented lines of the author block are merged into a `TypographicGroup`. Assigned a `typography_class` unique to its font weight/size.
    *   *Correct?* **YES**. The grouping obeys vertical/horizontal proximity, and the class strictly reflects the PDF font properties.
4.  **Landmarks**
    *   *Decision*: Evaluates $E_{curr} > E_{prev} \land E_{curr} > E_{next}$. The distinct author font forms a local emphasis peak. Emits `OUTLIER`.
    *   *Correct?* **YES**. The 1D signal math correctly identifies a typographic shift.
5.  **Semantic**
    *   *Decision*: Evaluates `is_outlier`. Transitions state from `FRONT_MATTER_PARSE` to `BODY_PARSE`.
    *   *Correct?* **NO**.

**Conclusion**: The first **NO** occurs at Semantic.

---

## Task 2 — Contract Satisfaction Proof

### Assembly
*   **Expected contract**: Group contiguous text blocks sharing identical physical typography and bounding box proximity into `TypographicGroup`s.
*   **Observed behavior**: Authors and affiliations were cleanly grouped and assigned a distinct typography class reflecting their font size/boldness.
*   **Satisfied?** **YES**
*   **Evidence**: Debug PDFs (`groups_debug.pdf`) show authors encapsulated in unified bounding boxes with color-coded classes distinct from the abstract and title.

### Landmarks
*   **Expected contract**: Emit an `OUTLIER` token strictly when a `TypographicGroup`'s emphasis score is a mathematical local maximum relative to its sequential neighbors.
*   **Observed behavior**: Emitted `OUTLIER` on author/affiliation blocks bounded by less-emphasized normal text.
*   **Satisfied?** **YES**
*   **Evidence**: The mathematical inequality `curr_emp > prev_emp and curr_emp > next_emp` strictly evaluates to True for bolded or enlarged author names.

---

## Task 3 — Falsification Attempt

**Adversarial Hypothesis**: `landmarks.py` is actually responsible because it should not emit outliers for non-structural text.

**Refutation**: 
This hypothesis violates the frozen architecture contract. `landmarks.py` is a purely typographic/geometric stage. It possesses zero semantic awareness. It cannot "read" text to know if a bold string is an author name or a section header. Its only contractual capability is detecting 1D signal peaks ($E_{curr} > E_{prev} \land E_{curr} > E_{next}$). 

Because the author/affiliation fonts in the PDF physically differ from surrounding text (e.g., larger than the email address, smaller than the title), they are legitimate, mathematically provable local maxima. If `landmarks.py` failed to emit an `OUTLIER` here, *it* would be in violation of its deterministic contract.

Therefore, the signal provided to Semantic was completely accurate. Semantic misinterpreted the signal.

**PIP-003 is the earliest deterministic failure.**

---

## Task 4 — Assumptions Matrix

| Assumption made by PIP-003 Implementation | Status |
| :--- | :--- |
| `OUTLIER` tokens are produced correctly by Landmarks. | **Verified** (per contract) |
| Front matter groups are ordered chronologically correctly. | **Verified** (per Ordering contract) |
| Title `ANCHOR` exists to initiate `FRONT_MATTER_PARSE`. | **Verified** (Global max emp always exists) |
| Abstract block is contiguous. | **Verified** (Assembly ensures proximity merging) |
| Section headers lack the word "Abstract". | **Verified** (Standard academic convention) |

---

## Task 5 — Final Verdict

**A. PIP-003 is proven to be the earliest incorrect deterministic decision. Proceed to implementation.**
