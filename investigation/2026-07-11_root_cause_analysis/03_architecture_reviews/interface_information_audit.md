# PIP-007 — Interface Information Audit
*Compiler Interface Verification*

## Task 1 — Stage Information Tables

| Stage | Information Available Internally | Information Exported | Information Lost |
| :--- | :--- | :--- | :--- |
| **Layout** | Raw glyphs, absolute 2D coords, raw font metadata, PDF hierarchy. | `TextBlock` (x,y,font,size,page), `DocumentLayout` (columns). | Precise inter-glyph spacing, vector graphics, image data. |
| **Ordering** | 2D geometric topology, column overlaps, reading paths. | 1D sorted sequence of `TextBlock`s. | Absolute 2D spatial relationships (flattened to 1D). |
| **Assembly** | 1D blocks, exact physical $\Delta y$ / $\Delta x$, raw font sizes. | `TypographicGroup` (merged text, bounds, quantized `typography_class`). | Intra-group formatting, continuous font scale (quantized). |
| **Landmarks** | Sequence of `typography_class` IDs, geometric bounds (y0, y1). | `LandmarkToken`s (`ANCHOR`, `OUTLIER` booleans). | **All non-peak transitions**, baseline geometry, gap magnitudes. |
| **Semantic** | `TypographicGroup`s, Landmark booleans, Lexical content. | `SemanticNode` AST. | None (Terminal stage). |

---

## Task 2 — Benchmark Information Tracking

**1. Spanner (Header: "1. INTRODUCTION")**
*   **Failure**: Misclassified as `AUTHORS` (dropped).
*   **Needed evidence**: Typographic transition (Class 3 $\rightarrow$ 6).
*   **First stage containing evidence**: **Assembly** (Computes `typography_class`).
*   **Did next stage receive it?**: YES (Landmarks received the class sequence).
*   **Did downstream receive it?**: NO.
*   **What was discarded?**: Landmarks evaluated the transition mathematically, determined it was not a peak ($6 < 8$), and discarded the transition event entirely by withholding the `OUTLIER` boolean.

**2. BERT (Adversarial Inline Bold)**
*   **Failure**: Phantom `SECTION_HEADER` spawning.
*   **Needed evidence**: Geometric Baseline Isolation (proof it does not share a line with body text).
*   **First stage containing evidence**: **Assembly** (Computes `y0`, `y1` bounds for the group).
*   **Did next stage receive it?**: YES (Landmarks).
*   **Did downstream receive it?**: NO.
*   **What was discarded?**: Landmarks evaluated only the scalar `typography_class`. It completely discarded the `y0`/`y1` coordinates and emitted `OUTLIER = True`. Semantic received the authorization to parse but lacked the geometric context to realize it was inline text.

---

## Task 3 — Information Flow Graph

*   **`font size` / `font weight`**
    *   *Created*: Layout
    *   *Transformed*: Assembly (Quantized into scalar integer `typography_class`)
    *   *Consumed*: Assembly
    *   *Disappears*: Mathematically abstracted away; Semantic operates on the class ID.
*   **`baseline` (`y0`, `y1`) / `bounding box`**
    *   *Created*: Layout
    *   *Transformed*: Ordering (Sorting) $\rightarrow$ Assembly (Merging limits)
    *   *Consumed*: Assembly
    *   *Disappears*: Discarded by Landmarks. Semantic never evaluates raw geometry.
*   **`typography_class`**
    *   *Created*: Assembly
    *   *Consumed*: Landmarks (Peak detection), Semantic (Hierarchy resolution).
    *   *Disappears*: End of pipeline.
*   **`is_outlier` boolean**
    *   *Created*: Landmarks
    *   *Consumed*: Semantic
    *   *Disappears*: End of pipeline.

---

## Task 4 — Interface Audits

1.  **Layout $\rightarrow$ Ordering**: No structural information is compressed or discarded.
2.  **Ordering $\rightarrow$ Assembly**: 2D topology is discarded in favor of 1D flow. This is safe and rarely reconstructed.
3.  **Assembly $\rightarrow$ Landmarks**: 
    *   *Compressed?* Yes (continuous fonts to discrete classes). 
    *   *Discarded?* Minor vertical gaps are abstracted into group bounds.
4.  **Landmarks $\rightarrow$ Semantic**: 
    *   *Compressed?* **YES**. The multidimensional transition matrix (change in class, gap size, baseline shift) is compressed into a 1-bit boolean (`OUTLIER`).
    *   *Discarded?* **YES**. Non-peak class transitions and geometric bounding boxes.
    *   *Required later?* **YES**. Semantic requires transitions (not just peaks) to find headers, and requires baseline geometry to ignore inline bold text.
    *   *Reconstructed?* **YES**. Because Semantic is starved of deterministic boundary evidence, it attempts to "reconstruct" structural intent using fragile lexical regexes (e.g., trying to guess if a string *looks* like a header to compensate for the missing geometric proof).

---

## Task 5 — The Landmark $\rightarrow$ Semantic Interface

Landmark currently exports `ANCHOR` and `OUTLIER`. 
Based on information theory and the benchmark corpus, these booleans are:
**D. Lossy**

By funneling a rich multidimensional array of typographic and geometric states into a binary token stream, the interface permanently deletes the nuance required to parse complex documents. It forces the downstream compiler stage (Semantic) to make decisions without sufficient evidence.

---

## Task 6 — Root Cause of Benchmark Failures

The failures across Spanner, Attention, and BERT are uniformly caused by:
**C. Information loss**

*Execution Trace Proof*: The algorithms themselves work exactly as programmed. Assembly computes a perfect `typography_class` mapping for Spanner. Assembly computes perfect geometric bounds for BERT. However, because the interface between Landmarks and Semantic is a bottleneck of two boolean flags, the computed evidence is lost in transit. Semantic fails because it executes on starved data, not because its own internal logic is mathematically flawed.

---

## Task 7 — State of the Lost Information

Was the required information already computed, or never computed?
**Already computed.**

The evidence needed to fix 100% of the observed semantic failures (typographic transitions, global baseline classes, y-axis overlap) already exists inside `context.assembled_groups`. The engineering problem is strictly a pipeline transmission failure—the downstream consumer is blocked from using data that was perfectly calculated by upstream producers.

---

## Task 8 — Final Audit Conclusion

Paperly's current architecture is **NOT** failing because the algorithms are wrong. 

It is failing because **the interfaces discard required evidence.** Specifically, the Landmark stage acts as a lossy compression filter that deletes critical geometric and typographic states before they reach Semantic Reconstruction.
