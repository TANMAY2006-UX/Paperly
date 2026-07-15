# Meaning of OUTLIER in Paperly
*Permanent Architecture Documentation*

## 1. The Compiler Contract of an OUTLIER
An `OUTLIER` token emitted by `landmarks.py` is a **strictly geometric and typographic signal**. 
The contract guarantees *only* that the emitted `TypographicGroup` possesses a `typography_class` whose computed emphasis represents a mathematical local maximum relative to its immediate sequential neighbors in the 1D reading flow (i.e., $E_{curr} > E_{prev} \land E_{curr} > E_{next}$).

The `OUTLIER` contract **guarantees nothing** about the text's linguistic meaning, structural role, or document zone. It is a syntactical lexer token (like a capital letter), not an AST node.

## 2. Typographic Classification Capabilities
For every class of block that may legitimately trigger a local typographic maximum, the responsibilities are defined as follows:

| Category | Can `landmarks.py` distinguish by typography alone? | Stage Owning Interpretation |
| :--- | :--- | :--- |
| **Structural Heading** (e.g., "1. Introduction") | **NO** | `semantic.py` |
| **Front Matter Emphasis** (e.g., Author Names, Affiliations) | **NO** | `semantic.py` |
| **Caption** (e.g., "Figure 1: ...") | **NO** | `semantic.py` (via regex heuristics) |
| **Figure Label** (e.g., Axis labels, charts) | **NO** | `semantic.py` (or Ordering/Assembly) |
| **Table Label** (e.g., Bold table headers/data) | **NO** | `semantic.py` |
| **Equation Label** (e.g., "(1)") | **NO** | `semantic.py` |
| **Running Header/Footer** | **NO** | `layout.py` (via geometric quorum) |
| **Unknown** (e.g., bolded inline text, drop caps) | **NO** | `semantic.py` |

## 3. The `SECTION_HEADER` Fallacy
**Should `semantic.py` assume every OUTLIER is a SECTION_HEADER?**
**NO.** 
Because `landmarks.py` operates purely on visual shifts, a bold author name, a bold number in a table, an equation label, or a localized font anomaly will all legitimately trigger the mathematical condition for an `OUTLIER`. Equating visual emphasis directly with structural hierarchy is a category error that conflates visual styling with document semantics.

## 4. Current Violations in `semantic.py`
`semantic.py` currently violates the `OUTLIER` contract in three distinct locations by assigning unconditional structural authority to a purely typographic signal:

1. **`FRONT_MATTER_PARSE` (PIP-003)**:
   ```python
   if is_outlier:
       if not text_lower.startswith("abstract"):
           state = ParserState.BODY_PARSE
   ```
   *Violation*: It falsely equates any typographic outlier in the preamble with the onset of the structural Body zone, ignoring Front Matter Emphasis.

2. **`BODY_PARSE` (PIP-004)**:
   ```python
   # Fallthrough after specific checks
   else:
       # Body Section Header Resolution
       new_section.children.append(SemanticNode(node_type=SemanticType.SECTION_HEADER, group=group))
   ```
   *Violation*: It unconditionally promotes any unhandled outlier (like bold table numbers or equations) to a structural `SECTION_HEADER` without requiring any lexical proof (e.g., numbering, length, title-casing).

3. **`REFERENCES_PARSE`**:
   ```python
   elif is_outlier:
       new_section.children.append(SemanticNode(node_type=SemanticType.SECTION_HEADER, group=group))
   ```
   *Violation*: It unconditionally assumes any outlier inside the references block is a new structural Section Header, fragmenting the bibliography.

## 5. Restoring the Contract
The smallest deterministic change to restore correct responsibilities across the architecture is to **demote the authority of the OUTLIER token** within `semantic.py`. 

`semantic.py` must treat `is_outlier` merely as a *trigger* to perform state-specific lexical and structural evaluations (e.g., checking if the text matches `^\d+\.\s`, checking the stack depth, or validating text length). If an `OUTLIER` fails these semantic proofs, `semantic.py` must gracefully downcast it to a standard content node (e.g., `PARAGRAPH`, `AUTHORS`, or `REFERENCES`) appropriate for the current state, rather than blindly assuming structural significance.
