# Runtime Evidence Audit

## Objective
To establish runtime facts regarding exactly what information is available to Semantic Reconstruction when processing the benchmark papers.

---

## Task 1 — TypographicGroup Fields

The object passed into `reconstruct_semantics()` is `context: ExtractionContext`, which contains `context.assembled_groups` (a list of `TypographicGroup`).

| Field | Type | Filled By | Runtime Example (Spanner Header) |
|-------|------|-----------|----------------------------------|
| `group_id` | `str` | Assembly | `"aaef8724"` |
| `raw_text` | `str` | Assembly | `"'1. INTRODUCTION'"` |
| `display_text` | `str` | Assembly | `"'1. INTRODUCTION'"` |
| `x0` | `float` | Assembly | `0.09259259259259259` |
| `y0` | `float` | Assembly | `0.5413418663872613` |
| `x1` | `float` | Assembly | `0.25640652503496336` |
| `y1` | `float` | Assembly | `0.5537951999240451` |
| `typography_class` | `int` | Assembly | `6` |
| `source_blocks` | `List[TextBlock]` | Assembly | `[[0] font: Helvetica-Bold, size: 8.966...]` |
| `evidence_vector` | `EvidenceVector` | Assembly | `physical_is_bold: True` |
| `repair_history` | `List[str]` | Assembly | `[]` |

---

## Task 2 — Fields Actually Read by Semantic

| Field | Exists | Read | Never Read |
|-------|--------|------|------------|
| `group_id` | YES | YES | |
| `raw_text` | YES | | YES |
| `display_text` | YES | YES | |
| `x0, y0, x1, y1`| YES | | YES |
| `typography_class`| YES | YES* | |
| `source_blocks` | YES | | YES |
| `evidence_vector`| YES | | YES |
| `repair_history`| YES | | YES |

*\* `typography_class` is read, but primarily used for nested section depth resolution and universal body computation, not for initial structural filtering.*

---

## Task 3 — Unread Fields Analysis

**Why are bounding boxes (`x0`, `y0`, `x1`, `y1`) and `evidence_vector` never read?**
This is intentional by design. The architectural contract of Paperly assumes that all geometric clustering and physical measurement tasks belong to upstream stages (Layout, Ordering, Assembly). Semantic acts strictly as a lexical and topological parser operating on an abstract 1D token stream.
*Code reference*: In `semantic.py`, coordinates are never referenced. `typography_class` is used as an abstract integer substitute for `evidence_vector.physical_dominant_size`.

---

## Task 4 — Spanner Failure Replay

At the exact moment Semantic processes the header, the runtime object is:
*   **Text**: `"1. INTRODUCTION"`
*   **Typography class**: `6`
*   **Bounding box**: `x0: 0.092, y0: 0.541, x1: 0.256, y1: 0.553`
*   **Font**: `Helvetica-Bold`
*   **Size**: `8.966`
*   **Bold**: `True`
*   **Group id**: `"aaef8724"`

**Could Semantic have recognized this header WITHOUT Landmark?**
**YES**. Semantic computes `universal_body_class` directly from `context.assembled_groups`. For Spanner, body text is class `8`. The header is class `6`. Semantic has the full `TypographicGroup` object and could trivially verify `group.typography_class != universal_body_class` to identify it as a structural candidate.

---

## Task 5 — BERT Failure Replay

At the exact moment Semantic processes the header:
*   **Text**: `"1 Introduction"`
*   **Typography class**: `13`
*   **Bounding box**: `x0: 0.120, y0: 0.661, x1: 0.260, y1: 0.675`
*   **Font**: `NimbusRomNo9L-Medi`
*   **Size**: `11.955`
*   **Bold**: `True`

**Could Semantic have recognized this header WITHOUT Landmark?**
**YES**. Body text for BERT is class `9`. `13 != 9`. Furthermore, if an inline bold word appeared, Semantic possessed the geometric bounds (`y0`/`y1`) needed to verify it was structurally identical to the surrounding baseline, independent of Landmark's tokens.

---

## Task 6 — Attention Failure Replay

At the exact moment Semantic processes the abstract header:
*   **Text**: `"Abstract"`
*   **Typography class**: `5`
*   **Bounding box**: `x0: 0.463, y0: 0.425, x1: 0.536, y1: 0.440`
*   **Font**: `NimbusRomNo9L-Medi`
*   **Size**: `11.955`
*   **Bold**: `True`

**Could Semantic have recognized this header WITHOUT Landmark?**
**YES**. The class `5` diverges from the body class, signaling a structural transition that Semantic could intercept independently.

---

## Task 7 — Benchmark Failure Classification

For every benchmark failure (Spanner missing headers, BERT ghost sections, Attention missing abstract):

**B. Semantic had the information but ignored it.**

*Execution Trace Proof*: 
Semantic receives `context.assembled_groups`, which contains perfect typographic classes, perfect bold flags, and perfect geometric bounding boxes for every single block. The information required to accurately parse every document *is physically present in Semantic's memory at runtime*. 
However, Semantic deliberately restricts its structural candidate filtering to `if is_outlier:`. It voluntarily ignores the rich, accurate evidence embedded in `group.typography_class` and `group.y0`, choosing to trust a flawed upstream boolean instead of the concrete data already passed to its function.

---

## Task 8 — Verdict

The runtime evidence unequivocally proves that Semantic Reconstruction possesses all required structural evidence (geometry, physical sizes, transition classes) inside `TypographicGroup`. 
The parser fails not because the pipeline discarded the evidence, but because `semantic.py`'s control flow is architected to ignore its own inputs, gating execution behind Landmark's oversimplified booleans.
