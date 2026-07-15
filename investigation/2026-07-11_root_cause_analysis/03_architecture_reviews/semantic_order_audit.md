# Semantic Verification Order Audit
*Final Design Freeze*

## 1. Verifier Ordering & Ambiguity Analysis

The semantic verification pipeline operates strictly on the compiler principle of "Most Specific Before Most General." Every verifier removes a distinct layer of ambiguity.

### `FRONT_MATTER_PARSE` Chain

**1. `verify_abstract()` $\rightarrow$ `verify_section_header()`**
*   **Why**: "Abstract" is a definitive structural keyword closing the preamble. Reversing the order allows generic section matchers to steal numbered abstracts.
*   **Ambiguity Input**: "1. Abstract" (`is_outlier=True`)
*   **Current Result**: `ABSTRACT` node (State remains Front Matter).
*   **Reversed Result**: `SECTION_HEADER` node (Premature transition to Body).

**2. `verify_section_header()` $\rightarrow$ `verify_email()`**
*   **Why**: A valid section header proves the onset of the body. If email verification ran first, a section header containing a contact email would incorrectly remain in the front matter.
*   **Ambiguity Input**: "Introduction (reach me at intro@author.com)" (`is_outlier=True`)
*   **Current Result**: `SECTION_HEADER` (Transitions to Body).
*   **Reversed Result**: `AUTHORS` (Fails to transition to Body).

**3. `verify_email()` $\rightarrow$ `verify_affiliation()`**
*   **Why**: The `@` symbol uniquely identifies an email address, superseding fuzzy affiliation keyword matches (like "university").
*   **Ambiguity Input**: "author@university.edu"
*   **Current Result**: `AUTHORS` (via email regex).
*   **Reversed Result**: `AFFILIATION` (Stolen by "university" keyword).

**4. `verify_affiliation()` $\rightarrow$ `verify_author()`**
*   **Why**: Authors are defined by the *absence* of structural or institutional evidence. Reversing the order makes the author verifier a greedy catch-all for affiliations.
*   **Ambiguity Input**: "Department of Computer Science"
*   **Current Result**: `AFFILIATION`.
*   **Reversed Result**: `AUTHORS`.

**5. `verify_author()` $\rightarrow$ `verify_paragraph()`**
*   **Why**: In the front matter, any text failing institutional/structural checks is assumed to be an author or implicit preamble text.
*   **Ambiguity Input**: "James C. Corbett"
*   **Current Result**: `AUTHORS`.
*   **Reversed Result**: `PARAGRAPH`.

### `BODY_PARSE` Chain

**6. `verify_reference_header()` $\rightarrow$ `verify_appendix()`**
*   **Why**: Terminal transitions must evaluate sequentially based on specificity. (Order is mostly commutative, but References strictly terminates the main body).

**7. `verify_appendix()` $\rightarrow$ `verify_section_header()`**
*   **Why**: "Appendix" is a highly specific semantic zone. Reversing the order strips it of its zone-transition authority, degrading it to a generic section.
*   **Ambiguity Input**: "Appendix A" (`is_outlier=True`)
*   **Current Result**: `SECTION_HEADER` (Transitions to Appendix Parse).
*   **Reversed Result**: `SECTION_HEADER` (Remains in Body Parse).

**8. `verify_section_header()` $\rightarrow$ `verify_caption()`**
*   **Why**: Captions are mutually exclusive with section headers via negative evidence (Section headers reject "Figure" prefixes). The order is mathematically commutative, but placing structural verification first preserves the AST hierarchy.

**9. `verify_caption()` $\rightarrow$ `verify_footnote()`**
*   **Why**: Captions are structural objects; footnotes are layout leaks.
*   **Ambiguity Input**: "Figure 1."
*   **Current Result**: `CAPTION`.
*   **Reversed Result**: `CAPTION` (Footnote regex fails).

**10. `verify_footnote()` $\rightarrow$ `verify_paragraph()`**
*   **Why**: Footnote verification is the final attempt to extract a layout artifact before surrendering to the generic text fallback.

---

## 2. Principle Proof (Specific Before General)

| Verifier | Classification | Reason for Order |
| :--- | :--- | :--- |
| `verify_abstract()` | **Structural (Specific)** | Fundamentally alters parsing context via strict keywords. |
| `verify_reference_header()`| **Structural (Specific)** | Fundamentally alters parsing context via strict keywords. |
| `verify_appendix()` | **Structural (Specific)** | Fundamentally alters parsing context via strict keywords. |
| `verify_section_header()` | **Structural (General)** | Alters context based on broad numeric/alphabetic heuristics. |
| `verify_caption()` | **Object (Specific)** | Lexically strict object extraction. |
| `verify_email()` | **Metadata (Specific)** | Symbol-strict (`@`) metadata extraction. |
| `verify_affiliation()` | **Metadata (Specific)** | Keyword-strict metadata extraction. |
| `verify_author()` | **Metadata (General)** | Generic fallback for front-matter entities. |
| `verify_footnote()` | **Object (General)** | Generic fallback for layout leaks. |
| `verify_paragraph()` | **Content (Generic Fallback)** | Universal leaf node. |

The pipeline naturally degrades from structurally transformative keywords to strict regex objects, down to fuzzy metadata, and finally to the generic text fallback.

---

## 3. Chain Reduction Proof

*   **Can any verifier be merged or removed?** **NO.**
*   Every verifier enforces a unique combination of `is_outlier` requirements, regex patterns, and negative evidence. More importantly, every verifier dictates a *unique state transition* or *unique SemanticNode creation*. Merging `verify_email` and `verify_affiliation` would obscure their distinct lexical proofs. Merging `verify_reference_header` and `verify_appendix` would convolute the state machine transitions.

---

## 4. Hidden Assumptions Audit

1.  **English-only keywords**: Relies entirely on English ("Abstract", "References", "University", "Figure"). *Acceptable for Paperly v1.*
2.  **Numbering conventions**: Relies on Arabic (`^\d+\.\s`) and Roman (`^[IVX]+\.\s`). Alpha-numeric prefixes (e.g., `A1.`) may fail. *Acceptable for Paperly v1.*
3.  **Title casing**: Assumes academic standard capitalization for optional section header evidence. *Acceptable for Paperly v1.*
4.  **Implicit structure limitation**: Completely ignores unlabeled sections and implicit abstracts. *Acceptable deterministic limitation for Paperly v1 (O(N) bound).*

---

## 5. Implementation Readiness

### List A: Implementation Tasks (Code Generation)
*   Refactor `reconstruct_semantics()` to sequentially chain `if/elif/else` blocks mirroring the exact verification order.
*   Enforce `is_outlier` purely as a condition *inside* the verifiers (e.g., `if is_outlier and re.match(...)`), never as a global state-trigger.
*   Implement the regex patterns defined in the Semantic Verification Rules document.
*   Ensure the `section_stack` popping and pushing logic is correctly embedded within the True branch of `verify_section_header()`.

### List B: Open Questions (Pending Benchmark Evidence)
*   Does `FOOTNOTE` require a dedicated SemanticType, or is tagging it as `PARAGRAPH` sufficient for downstream consumers?
*   Should `AFFILIATION` be decoupled from `AUTHORS` in the final SemanticTree output, or kept merged for simplicity?

---

## 6. Final Recommendation

**Semantic design is frozen.**

I recommend freezing the semantic design permanently and beginning implementation immediately. The deterministic logic is mathematically sound, bounds complexity to O(N), and resolves all observed pipeline regressions without violating the frozen architecture constraints.
