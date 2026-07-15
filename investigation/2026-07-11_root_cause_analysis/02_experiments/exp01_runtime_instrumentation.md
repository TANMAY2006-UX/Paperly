# EXP-01 Runtime Instrumentation
*Compiler Pass Diagnostics: Landmark Evaluation*

## Task 1, 2, & 3 — Tracing Landmark Decisions

### Sub-Trace: Spanner (False Negative Header)
```text
----------------------------------
Page: 0
Group ID: 8e9524b2
Display Text: 1. INTRODUCTION
Typography Class: 6
Raw Font Size: 8.9664
Bold: True
Prev Class: 3
Next Class: 8
Current Local Maximum Decision: False
Current Anchor Decision: False
Current OUTLIER Decision: False
Reason: curr <= next
----------------------------------
```

### Sub-Trace: BERT (False Positive Inline Peak)
```text
----------------------------------
Page: 3
Group ID: 0524a1ff
Display Text: MLM
Typography Class: 12
Raw Font Size: 11.9552
Bold: True
Prev Class: 9
Next Class: 9
Current Local Maximum Decision: True
Current Anchor Decision: False
Current OUTLIER Decision: True
Reason: Local maximum
----------------------------------
```

### Sub-Trace: Attention Is All You Need (Valid Peak)
```text
----------------------------------
Page: 0
Group ID: 2675f547
Display Text: Abstract
Typography Class: 5
Raw Font Size: 11.9552
Bold: True
Prev Class: 12
Next Class: 9
Current Local Maximum Decision: True
Current Anchor Decision: False
Current OUTLIER Decision: True
Reason: Local maximum
----------------------------------
```

---

## Task 4 — Corpus Statistics

### Spanner
*   **Number of groups**: 379
*   **Number of anchors**: 1
*   **Number of outliers**: 41
*   **Number of rejected candidates**: 338
*   **Average paragraph length**: 196.7 chars
*   **Maximum paragraph length**: 3109 chars

### BERT
*   **Number of groups**: 611
*   **Number of anchors**: 1
*   **Number of outliers**: 73
*   **Number of rejected candidates**: 538
*   **Average paragraph length**: 219.0 chars
*   **Maximum paragraph length**: 3968 chars

### Attention Is All You Need
*   **Number of groups**: 280
*   **Number of anchors**: 1
*   **Number of outliers**: 37
*   **Number of rejected candidates**: 243
*   **Average paragraph length**: 115.4 chars
*   **Maximum paragraph length**: 1495 chars

---

## Task 5 & 6 — Benchmark Aggregation

*All data represents exact runtime execution across Spanner, BERT, and Attention Is All You Need.*

### Landmark Recall Efficiency
*   **Headers expected**: 25
*   **Headers detected**: 14 (56.0%)
*   **Headers missed**: 11 (44.0%)

### False Positive Promotion Rate
*   **False outliers (Total)**: 134
*   **Paragraphs promoted (Incorrect)**: 134
*   **Paragraphs rejected (Correct)**: 1057
*   **Captions promoted (Incorrect)**: 3
*   **Captions rejected (Correct)**: 32

### Structural Contamination Ratio
*   Total true headers emitted: 14
*   Total false items emitted: 137
*   **Contamination Rate**: For every 1 valid header `Landmarks` permits, it permits ~9.7 false positive inline words or equations.
