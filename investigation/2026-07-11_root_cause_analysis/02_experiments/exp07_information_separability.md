# EXP-07 Information Separability Analysis
*Observational Measurement of Set B Entanglement*

## Task 1 — Partitioning Set B

Using the benchmark ground truth, the 678 objects in Set B (typographically distinct from body, but not local maxima) were partitioned into:
*   **True Structural Objects (TP)**: 103 (e.g., missed section headers, authors, titles)
*   **False Positives (FP)**: 575 (e.g., table values, inline math, captions)

---

## Task 2 & 3 — Attribute Distributions

For every object, we extracted purely observable physical attributes natively available in the `Assembly` stage (prior to Semantic).

| Attribute | True Structural Objects (N=103) | False Positives (N=575) | Overlap |
| :--- | :--- | :--- | :--- |
| **Physical Bold** | True: 31% <br> False: 69% | True: 6% <br> False: 94% | **High**. While TP is 5x more likely to be bold, 69% of structural objects are NOT bold. |
| **Block Count** | Median: 1 <br> Max: 6 | Median: 1 <br> 75th: 3 <br> Max: 26 | **High**. Complete overlap for simple text (1 block), though complex tables (7+ blocks) exclusively belong to FP. |
| **Char Length** | Median: 13 <br> 75th: 21.5 | Median: 23 <br> 75th: 67.5 | **High**. TPs are generally shorter (headers), but overlap heavily with FP (short table values/math). |
| **Width Ratio** | Median: 0.12 <br> 75th: 0.20 | Median: 0.20 <br> 75th: 0.36 | **High**. Both populations heavily populate the 0.0 - 0.4 width range. |
| **Line Count** | Median: 1 <br> Max: 1 | Median: 1 <br> Max: 1 | **Total**. Identical distributions. |
| **Page Position** | Top: 35% <br> Mid: 45% <br> Bot: 19% | Top: 58% <br> Mid: 25% <br> Bot: 15% | **High**. FPs are slightly more clustered at the top, but overlap exists everywhere. |

---

## Task 4 — Separability Evaluation

Can these attributes separate the two populations without semantic context?

*   **Physical Bold**: **PARTIALLY**. Isolates a strong subset of headers, but rejects the 69% of valid structural objects that are unbolded.
*   **Block Count**: **PARTIALLY**. Perfect for rejecting complex grid layouts (tables/math), but entirely useless for separating a 1-block header from a 1-block table cell.
*   **Char Length & Width**: **PARTIALLY**. Good for rejecting long captions, but useless for distinguishing short headers from short noise.
*   **Line Count**: **NO**.
*   **Page Position**: **NO**.

---

## Task 5 — Attribute Ranking (Information Gain)

Ranked by their ability to independently filter False Positives without destroying True Positives:
1.  **Block Count**: Strongly isolates complex grid noise (Tables/Equations) with zero risk to headers (which never exceed 6 merged blocks).
2.  **Physical Bold**: Provides the highest signal-to-noise ratio, though its utility is limited to bold-heavy documents.
3.  **Width Ratio / Char Length**: Provides weak thresholds to reject massive paragraph-length captions.
4.  **Page Position**: Negligible value.
5.  **Line Count**: Zero value.

---

## Task 6 — Final Report

**1. Is Set B fundamentally inseparable, or can existing Assembly information separate it?**
Set B is **fundamentally inseparable** using purely geometric and typographic attributes. While extreme values (like block counts > 7) can cleanly reject some noise, the dense core of the data (short, 1-block, non-bold strings) contains a complete entanglement of True Positives (Subsections/Headers) and False Positives (Table Cells/Inline Math). 

**2. If separable, which existing attribute provides the largest reduction in false positives?**
While not perfectly separable, `Block Count` provides the largest safe reduction in false positives. Rejecting groups with `block_count > 6` safely eliminates large fragmented tables and equations without harming a single structural object.

**3. What evidence remains missing?**
The missing evidence is **Semantic Regular Expressions**. A short, non-bold, 1-block string like "1.1 Introduction" is physically identical to a short, non-bold, 1-block string like "0.452". The *only* evidence capable of breaking the Set B entanglement is the textual content itself (the `Semantic` stage). By filtering Set B at the `Landmark` stage before regexes can be applied, the pipeline is mathematically guaranteeing failure.
