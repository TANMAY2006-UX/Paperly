# EXP-06 Candidate Set Measurement
*Observational Information Audit (No Architecture Changes)*

## Task 1 & 2 — Candidate Enumeration & Ground Truth Comparison

Every TypographicGroup in the corpus was categorized into three sets based on pure typographic attributes. We then measured how many of the 199 true structural objects (Titles, Abstracts, Authors, Section Headers, Subsections, References) landed in each set.

| Set | Definition | Total Groups | Contains Structural Objects | Structural Recall |
|---|---|---|---|---|
| **Set A** | `is_outlier == True` (Admitted by Landmark) | 151 | **59** | 29.65% |
| **Set B** | `!is_outlier` AND `class != universal_body_class` | 678 | **103** | 51.76% |
| **Set C** | `class == universal_body_class` | 422 | **37** | 18.59% |

*(Note: Set A + Set B = 81.41% total structural recall. The remaining 18.59% in Set C are headers that are physically identical to body text).*

---

## Task 3 — Noise Analysis

For the dominant false positive categories, we tracked which typographic set contained the noise.

| Noise Category | Set A (Outlier) | Set B (!Outlier, != UBC) | Set C (== UBC) |
|---|---|---|---|
| **INLINE_BOLD** | 7 | 24 | 0 |
| **TABLE_VALUE** | 10 | 48 | 31 |
| **CAPTION** | 8 | 23 | 14 |
| **DISPLAY_EQUATION** | 4 | 9 | 31 |
| **INLINE_MATH** | 2 | 17 | 24 |
| **FOOTNOTE** | 0 | 3 | 8 |

---

## Task 4 — Coverage Metrics

**Set A (`is_outlier` gate currently used by Semantic)**
*   **Recall**: 29.65%
*   **Precision**: 39.07%

**Set B (Information currently discarded by Semantic)**
*   **Recall**: 51.76%
*   **Precision**: 15.19%

**Set A ∪ B (All Typographically Distinct Text)**
*   **Recall**: 81.41%
*   **Precision**: 19.54%

---

## Task 5 — Information Gain

**Does Set B contain information that Landmark currently discards?**
**Yes.** 

**How much?**
Set B contains **103 structural objects**, which represents **51.76%** of all valid structural information in the document. 

**Exactly which ones?**
These are structural elements that are typographically distinct from the body text (meaning they have unique font sizes or weights) but fail the strict local maximum check. This includes:
1.  **Valley Headers**: Section headers (like "1. INTRODUCTION" in Spanner) that are physically smaller than surrounding body text.
2.  **Plateau Peaks**: Subsections or Authors that share identical typography with adjacent blocks, thus failing the `curr < prev` strict peak test.

By filtering exclusively on `is_outlier` (Set A), the Semantic parser is literally blinding itself to over half the structural layout of the document.

---

## Task 6 — Final Recommendation

**What evidence have we learned?**
1.  **The firewall is blinding the parser:** The assumption that `OUTLIER == All Structural Info` is disastrously incorrect. `Landmarks` captures only ~30% of structural objects.
2.  **The information exists:** The `Assembly` stage correctly tags 81.41% of structural objects with unique, non-body typography (Set A ∪ Set B). 
3.  **Invisible Headers (Set C):** 18.59% of headers are completely identical to body text. Typographic math *cannot* detect these. Only regex or structural parsing can find them.

**What architectural questions remain unanswered?**
If `Semantic` removes the `is_outlier` firewall and begins evaluating all 829 groups in Set A and Set B, its Recall will jump from 30% to 81%. However, its Precision will plummet to 19% because it will simultaneously expose itself to hundreds of `TABLE_VALUE`, `INLINE_BOLD`, and `CAPTION` false positives. 

The unanswered architectural question is: **Can the `Semantic` stage natively filter that noise using regex and bounding boxes (EXP-05), or will it be overwhelmed without the Landmark firewall?**
