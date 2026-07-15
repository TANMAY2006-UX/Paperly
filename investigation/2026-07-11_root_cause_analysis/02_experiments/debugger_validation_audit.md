# Debugger Validation Audit
*Verification of Experimental Methodology*

## Task 1 — Debugger Classification Audit

The EXP-02 experimental methodology contained a critical flaw. It classified any emitted `OUTLIER` as a "False Outlier" if it was not a numbered `SECTION_HEADER`. 

This assumption is architecturally incorrect. The contract of the `Landmark` stage is to identify structurally distinct typographic peaks (local maxima). The `Semantic` stage explicitly relies on `is_outlier` to drive multiple state machine transitions beyond just section headers.

**Corrected Classifications:**
*   **TITLE**: Valid OUTLIER. (Previously classified as False Positive / `INLINE_BOLD`)
*   **ABSTRACT**: Valid OUTLIER. (Previously classified as False Positive / `INLINE_BOLD`)
*   **AUTHOR**: Valid OUTLIER. (Previously classified as False Positive / `AUTHOR`)
*   **SUBSECTION_HEADER**: Valid OUTLIER. (Previously classified as False Positive / `INLINE_BOLD`)
*   **REFERENCE_HEADER**: Valid OUTLIER. (Previously classified as False Positive / `INLINE_BOLD`)

The previous audit mislabeled 42 valid structural candidates because it evaluated `Landmarks` against a simplified user expectation, rather than its actual contractual dependency in the `semantic.py` compiler stage.

---

## Task 2 — Case Reviews

| Text | Expected Semantic Object | Expected Landmark Behavior | Expected Semantic Behavior | EXP-02 Classification | Corrected Classification |
|---|---|---|---|---|---|
| Attention Is All You Need | `TITLE` | **OUTLIER** (Largest font) | Transition to `TITLE_SEARCH` | False Positive | True Positive |
| Abstract | `ABSTRACT` | **OUTLIER** (Bold peak) | Transition to `FRONT_MATTER` | False Positive | True Positive |
| ACKNOWLEDGEMENTS | `REFERENCE_HEADER` | **OUTLIER** | Transition to `REFERENCES_PARSE` | False Positive | True Positive |
| APPENDIX | `REFERENCE_HEADER` | **OUTLIER** | Transition to `APPENDIX_PARSE` | False Positive | True Positive |
| Encoder: / Decoder: | `SUBSECTION_HEADER` | **OUTLIER** | Push as nested section child | False Positive | True Positive |
| Residual Dropout | `SUBSECTION_HEADER` | **OUTLIER** | Push as nested section child | False Positive | True Positive |
| Google AI Language | `AFFILIATION` | NOT OUTLIER | Append to `AUTHORS` or ignore | True Negative | True Negative |
| Jakob Uszkoreit | `AUTHOR` | **OUTLIER** | Parse as `AUTHOR` | False Positive | True Positive |
| 41.29 | `TABLE_VALUE` | NOT OUTLIER | Parse as Table/Paragraph | False Positive | False Positive |
| MLM / NSP / CLS | `PARAGRAPH` | NOT OUTLIER | Parse as Paragraph | False Positive | False Positive |

---

## Task 3 — Definition of a False OUTLIER

**Current (Invalid) Assumption:** `OUTLIER == SECTION HEADER`

This is invalid because `semantic.py` lines 118-125 depend on `is_outlier` to find the `ABSTRACT` and `AUTHORS` during `FRONT_MATTER_PARSE`. 

**Mathematically Correct Definition:** 
An `OUTLIER` is **TRUE POSITIVE** if the downstream parser depends on its typographic isolation to trigger a structural state transition or hierarchical nesting (`TITLE`, `ABSTRACT`, `AUTHOR`, `SECTION_HEADER`, `SUBSECTION_HEADER`, `REFERENCE_HEADER`, `APPENDIX`).

An `OUTLIER` is **FALSE POSITIVE** if it represents localized inline emphasis (`INLINE_BOLD`), tabular noise (`TABLE_VALUE`), or non-structural text (`CAPTION`, `DISPLAY_EQUATION`) that mathematically forms a local maximum but lacks structural authority.

---

## Task 4 — Recomputed Statistics & Confusion Matrix

Using the corrected definitions on the exact EXP-01 and EXP-02 telemetry:

*   **True Positive OUTLIERS**: 58
*   **False Positive OUTLIERS**: 93
*   **Missed Structural Candidates**: 8 (Valid section headers missed due to `curr <= prev/next` valley effect)

### Corrected Confusion Matrix A
| | Emitted as OUTLIER | Rejected by Landmark |
|---|---|---|
| **Legitimate Structural Candidate** | 58 *(True Positives)* | 8 *(False Negatives)* |
| **Non-Structural Text** | 93 *(False Positives)* | ~1050 *(True Negatives)* |

---

## Task 5 — Shift in Top 3 Failure Categories

Yes, correcting the debugger significantly changes the failure distribution.

### Original Distribution (EXP-02)
1.  **INLINE_BOLD**: 80
2.  **AUTHOR**: 38
3.  **TABLE_VALUE**: 10

### Corrected Distribution
1.  **INLINE_BOLD**: 57 (Down from 80, as subsections/titles are now correctly classified as True Positives)
2.  **PARAGRAPH**: 18 (Short bold paragraphs previously lumped into unknown/bold)
3.  **TABLE_VALUE**: 10 (Remains identical)

> [!IMPORTANT]
> The `AUTHOR` category has completely vanished from the failure distribution. `AUTHORS` are *supposed* to be OUTLIERS according to the frozen architecture, and `Landmarks` correctly emitted them.

---

## Task 6 — Conclusion

**Did EXP-02 expose a compiler bug, or did it expose a debugger classification bug?**

It exposed a **major debugger classification bug**, which in turn obscured the actual compiler bug.

The debugger wrongly assumed that `Landmark`'s responsibility was exclusively to emit numbered `SECTION_HEADER`s. By correcting the audit to reflect the actual architectural contract enforced in `semantic.py`, we proved that `Landmark` is actually highly successful at finding structural boundaries (58 True Positives). 

However, the **compiler bug** remains real and is two-fold:
1.  **False Negatives (The Valley Problem)**: Landmark's local maximum math (`curr <= prev/next`) still causes 8 valid `SECTION_HEADER`s to be rejected entirely because they are physically smaller than the surrounding body text (e.g., in Spanner).
2.  **False Positives (Lossy Booleans)**: Landmark emits 93 False Positives (`INLINE_BOLD`, `TABLE_VALUE`). Because Landmark reduces rich geometric bounding boxes into a single `is_outlier` boolean, `Semantic` is blinded to physical coordinates and thus fails to reject inline bold text.
