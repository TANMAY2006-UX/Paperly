# Landmark ↔ Semantic Interface Audit

## Task 1 — Semantic's Assumptions of Landmark Tokens
In `extractor/semantic.py`, the parser branches aggressively on Landmark tokens:
1.  **`TITLE_SEARCH`**: `if is_anchor:`
    *   **Assumption**: `is_anchor` represents the absolute top-level, globally dominant Document Title.
2.  **`FRONT_MATTER_PARSE`**: `if is_outlier:`
    *   **Assumption**: `is_outlier` represents a structural candidate that could break front matter (i.e., the Abstract header or the start of the Body).
3.  **`BODY_PARSE`**: `if is_outlier:`
    *   **Assumption**: `is_outlier` represents a structural candidate that dictates a `SECTION_HEADER`, `APPENDIX`, or `REFERENCES` break.
4.  **`REFERENCES_PARSE` / `APPENDIX_PARSE`**: `if is_outlier:`
    *   **Assumption**: `is_outlier` represents a structural sub-divider within the end matter.

---

## Task 2 — Are These Assumptions Guaranteed by Landmark?
*   **`is_anchor` = Document Title?**
    *   **PARTIALLY**. Landmark guarantees the mathematical global maximum of `typography_class`. While usually the Title, if a publisher uses a massive drop-cap letter or a giant logo parsed as text, it becomes the anchor instead.
*   **`is_outlier` = Structural Candidate?**
    *   **NO**. Landmark strictly guarantees a mathematical *Local Maximum* ($C_{curr} > C_{prev} \land C_{curr} > C_{next}$).
    *   *Runtime Evidence*: In Spanner, the "1. INTRODUCTION" header is smaller than the body text, forming a mathematical valley. Landmark correctly refuses to emit `OUTLIER`. An inline bold word forms a peak; Landmark correctly emits `OUTLIER`. Landmark guarantees local math, but Semantic assumes global structure.

---

## Task 3 — Dependency Table

| Semantic Decision | Information Required | Currently Obtained From | Actually Guaranteed? | Responsible Owner |
| :--- | :--- | :--- | :--- | :--- |
| **`TITLE`** Node | Highest structural block | `is_anchor` | PARTIALLY | Semantic (Global Context) |
| **`FRONT_MATTER`** Exit | Front matter boundary | `is_outlier` | NO | Semantic (Global Context) |
| **`SECTION_HEADER`** Node | Structural candidate | `is_outlier` | NO | Semantic (Global Context) |
| **`REFERENCES`** Node | Reference boundary | `is_outlier` | NO | Semantic (Global Context) |

---

## Task 4 — Benchmark Failures (First Invalid Assumption)
In **Spanner**, the parser never enters `BODY_PARSE`, trapping all text as `AUTHORS`.
*   **The first invalid semantic assumption**: Semantic assumed that `NOT OUTLIER $\implies$ NOT Structural Candidate`.
*   **Was it guaranteed?**: No. Because "1. INTRODUCTION" was physically smaller than body text, Landmark evaluated it as a valley and withheld the `OUTLIER` token. Semantic blindly trusted that the absence of an `OUTLIER` token meant the absence of structure, bypassing its own lexical checks and falling back to `AUTHORS`.

---

## Task 5 — Information Theory: What Semantic Actually Requires
**B. The raw typographic stream and should perform its own verification.**

*Information Theory Justification*: A "structural candidate" is a block that breaks the global flow of the document. Identifying this requires global context (e.g., knowing what the baseline body text is). Landmark is an $O(N)$ stateless, local stage ($prev, curr, next$). It is mathematically impossible for a local stage to reliably identify global structural boundaries without heuristics. Semantic possesses global context; therefore, Semantic must perform its own candidate filtering.

---

## Task 6 — Reconstructing Without OUTLIER
**Would Semantic still be theoretically capable of reconstructing the document if Landmark emitted nothing except `ANCHOR`?**

**YES.**
Semantic currently receives `context.assembled_groups`. It already contains a function `_compute_safe_body_class()` which establishes the global baseline typography. 
If Semantic simply replaced `if is_outlier:` with `if group.typography_class != universal_body_class:`, it would possess a perfectly accurate, globally-aware filter for structural candidates. It would successfully catch the Spanner headers, ignore inline text, and completely eliminate the need for upstream filtering.

*   **Redundant Responsibilities**: The entire `OUTLIER` emission logic in `landmarks.py` is redundant. It attempts to approximate structural candidates using local math, a task Semantic can do deterministically using global context.

---

## Task 7 — The Root Cause

**D. The interface between them**

*Support with Benchmark Evidence*:
Landmark's implementation of `Local Maximum` perfectly satisfies its mathematical contract. Semantic's lexical logic perfectly satisfies its structural contract. 
The failure lies strictly in the **Interface**. The interface tasks Landmark (a stateless, local component) with supplying a structural authorization token (`is_outlier`) to Semantic (a stateful, global component). Because Landmark lacks global context, its tokens inevitably misclassify adversarial layouts (like Spanner's small headers). Semantic blindly trusts this flawed interface, resulting in AST corruption. This is a textbook violation of separation of concerns.
