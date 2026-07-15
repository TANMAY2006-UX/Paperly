# Semantic Contract Audit
*Architectural Ownership Verification*

## Task 1 — TypographicGroup Fields

| Field | Available | Semantically Relevant | Architecturally Owned By |
|-------|-----------|-----------------------|--------------------------|
| `group_id` | YES | YES | Assembly |
| `raw_text` | YES | NO (Pre-repair) | Assembly |
| `display_text` | YES | YES | Assembly |
| `x0, y0, x1, y1`| YES | NO (Structurally superseded by reading order) | Layout / Assembly |
| `typography_class`| YES | YES | Assembly |
| `source_blocks` | YES | NO (Atomic units) | Layout |
| `evidence_vector` | YES | NO (Pre-quantization data) | Assembly |
| `repair_history` | YES | NO | Assembly |

---

## Task 2 — Semantic's Treatment of TypographicGroup

Semantic intentionally treats `TypographicGroup` as:
**B. An abstract token.**

*Code Support*: In `extractor/semantic.py`, Semantic strictly iterates over the 1D sequence (`for group in context.assembled_groups:`), evaluates lexical content via regex (`text_lower`), and compares relative hierarchy using scalar identifiers (`group.typography_class > header_group.typography_class`). It never executes 2D spatial clustering or physical distance mathematics. The object is treated purely as a sequential, pre-processed lexical token.

---

## Task 3 — Verification of Unread Fields

**`x0`, `y0`, `x1`, `y1`**
*   **Semantic is supposed to ignore this.**
*   *Support*: Assembly is the architectural stage strictly responsible for geometric proximity and overlap clustering. If Semantic were to read bounding boxes to determine structural boundaries, it would violate the architecture by dragging 2D spatial reasoning into a 1D lexical parser.

**`source_blocks`**
*   **Semantic is supposed to ignore this.**
*   *Support*: Assembly's contract is to merge broken lines into unified semantic clusters. Semantic should only interact with the merged `display_text`.

**`evidence_vector`**
*   **Semantic is supposed to ignore this.**
*   *Support*: The exact purpose of Assembly emitting a scalar `typography_class` is to quantize messy physical properties (font size, weight) into clean mathematical identifiers. The architecture explicitly intends for downstream stages to rely on the class ID, insulating them from raw physical measurements.

---

## Task 4 — Direct Geometric Reading by Semantic

If Semantic were modified to read geometry (`x0, y0...`) directly, it would:
**D. Change the architecture** (and inherently **B. Duplicate Assembly**)

*Support*: The Paperly architecture is a linear compilation pipeline (`Layout $\rightarrow$ Ordering $\rightarrow$ Assembly $\rightarrow$ Landmarks $\rightarrow$ Semantic`). The deliberate architectural boundary of Assembly is to transform 2D spatial geometry into 1D typographically uniform tokens. If Semantic requires 2D geometry to infer structure, it implies the architecture failed to encapsulate spatial reasoning within Assembly, thus requiring a fundamental redesign of pipeline responsibilities.

---

## Task 5 — The Intent of `is_outlier`

The code proves that `is_outlier` is intended to be:
**A. The only legal gateway into structural verification.**

*Code Support*: 
```python
if state == ParserState.FRONT_MATTER_PARSE:
    if is_outlier:
        if re.match(r'^(?:\d+\.?\s*)?abstract\b', text_lower, re.IGNORECASE):
        # ... other structural checks ...
    else:
        # Unconditional fallback to Paragraph / Authors
```
Semantic does not use `is_outlier` to skip expensive regexes conditionally; it uses it as a hard architectural firewall. If `is_outlier` is false, Semantic is explicitly programmed to assume the token is NOT a structural candidate and unconditionally forces it into a contiguous flow state (Paragraph/Authors). 

---

## Task 6 — Theoretical Removal of Landmark

Suppose Landmark were removed completely. Could Semantic still satisfy every documented contract?
**YES**.

*Explanation*: Semantic computes `universal_body_class` natively to identify standard text flow. Semantic possesses the exact `typography_class` sequence. By replacing `if is_outlier:` with `if group.typography_class != universal_body_class:` (and filtering captions), Semantic could independently and deterministically identify every structural candidate. It possesses complete global context, making the upstream `is_outlier` filter functionally redundant.

---

## Task 7 — Current Implementation Classification

The current implementation of Semantic Reconstruction is best classified as an:
**C. Architectural limitation**

*Evidence*:
1.  **Not an implementation bug**: `semantic.py` perfectly obeys its programmed logic and trusts its inputs as designed.
2.  **Not a contract violation**: Semantic properly treats Assembly's tokens as abstract, and relies on Landmark's signals, exactly as the pipeline interface mandates.
3.  **The Limitation**: The architecture mistakenly assigned the responsibility of "structural boundary filtering" to the Landmark stage. Because Landmark is stateless and lacks global context, it mathematically misses valid headers (like Spanner). Semantic trusts this flawed architectural interface, resulting in AST failures. The implementation accurately reflects a flawed architectural design.
