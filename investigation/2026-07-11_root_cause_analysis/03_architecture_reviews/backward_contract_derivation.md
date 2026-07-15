# Backward Contract Derivation
*Information Flow and Ownership Analysis*

## Task 1 — Required Information for Semantic Objects
To identify semantic objects from scratch, the following information MUST be known:
*   **TITLE**: Structurally dominant position, isolated at document start.
*   **AUTHORS**: Positioned post-title, lexically resembling names/entities, clustered.
*   **AFFILIATION**: Proximate to authors, typographically distinct/smaller, lexically institutional.
*   **ABSTRACT**: Positioned in front matter, contiguous text block, bounded by specific keywords or visual shifts.
*   **SECTION**: Breaks preceding text flow, typographically distinct and consistent relative to body text, often carrying numeric prefixes.
*   **SUBSECTION**: Breaks flow, hierarchically subordinate to a SECTION but dominant over body text.
*   **PARAGRAPH**: Contiguous text sharing uniform baseline typography, often indicated by geometric indentation or leading vertical gap.
*   **CAPTION**: Geometrically adjacent to visual regions, typographically distinct (often smaller), lexically prefixed.
*   **FIGURE / TABLE**: Geometric regions breaking normal reading flow, exhibiting bounding boxes or tabular alignment.
*   **REFERENCES**: Trailing position, repetitive hanging indents, specific lexical prefix.

---

## Task 2 — Dependency Matrix Partitioning

| Object | A. Purely Geometric | B. Purely Typographic | C. Lexical | D. Document Context |
| :--- | :--- | :--- | :--- | :--- |
| **TITLE** | First position | Maximum visual weight | None | Global unique max |
| **AUTHORS** | Proximate clustering | Distinct from title/body | Names | Front matter only |
| **AFFILIATION**| Proximate to authors | Distinct/Smaller | Institution | Front matter only |
| **ABSTRACT** | Contiguous block | Distinct margins/font | "Abstract" | Front matter only |
| **SECTION** | Vertical gap | Distinct from body flow | "1.", "Intro" | Hierarchy (Top level) |
| **SUBSECTION**| Vertical gap, indent | Distinct, lesser than Section | "1.1." | Hierarchy (Nested) |
| **PARAGRAPH** | Indent, vertical gap | Uniform baseline body | None | Inside body/abstract |
| **CAPTION** | Adjacent to object | Distinct/Smaller | "Fig.", "Tab." | Bound to object |
| **FIG / TABLE**| Bounding box / Grid | None / Tabular spacing | None | Float / Inline |
| **REFERENCES**| List structure | Hanging indent | "References" | End matter only |

---

## Task 3 — Legal Landmark Productions
Landmark must remain $O(N)$, deterministic, publisher agnostic, and language agnostic.
*   **A. Purely Geometric**: **YES**. It can observe physical gaps, alignments, and spatial relationships.
*   **B. Purely Typographic**: **YES**. It holds the quantized `typography_class` sequence.
*   **C. Lexical**: **NO**. It cannot read text, use regex, or match strings.
*   **D. Document Context**: **NO**. It cannot maintain global state or hierarchical AST logic.

---

## Task 4 — Information Ownership Assignment
To prevent overlap, responsibility is strictly partitioned:
*   **Ordering**: 1D sequence mapping (Left-to-right, top-to-bottom reading path).
*   **Assembly**: Local physical clustering (Merging lines into unified groups based on geometric overlap and identical typography).
*   **Landmark**: Typographic and geometric transitions (Signaling where stylistic regimes break in the 1D sequence).
*   **Semantic**: Lexical matching, global document context, hierarchy resolution, and AST construction.

---

## Task 5 — OUTLIER vs VISUAL_BOUNDARY
**Does Semantic actually need `OUTLIER`, `VISUAL_BOUNDARY`, or something else?**

From the dependency matrix, identifying Sections, Subsections, and Abstracts all require the same core signal: **Distinct from body flow**. Semantic already possesses the raw typographic class IDs to resolve hierarchy ($C_{group} > C_{header}$), but it relies on Landmark to filter *which blocks are structural candidates* requiring expensive lexical/hierarchical evaluation. 

If Landmark emits `OUTLIER` (peaks), it drops structurally vital "valleys" (smaller headers). If it emits `VISUAL_BOUNDARY` for every minor shift, it overwhelms Semantic with paragraphs and figures. 

Therefore, Semantic requires **ISOLATION**. It needs to know when a block stands apart typographically from the contiguous text surrounding it. The concept of an `OUTLIER` remains valid, but its mathematical definition must change from *peak* to *typographic isolation*.

---

## Task 6 — Information Flow Simulation (Spanner, Attention, BERT)

*   **Ordering Stage**:
    *   *Input*: 2D text blocks.
    *   *Output*: 1D reading sequence.
    *   *Lost Information*: Absolute 2D spatial relationships (e.g., this block was exactly 5px from the margin).
    *   *New Information*: Deterministic reading order.
*   **Assembly Stage**:
    *   *Input*: 1D block sequence.
    *   *Output*: TypographicGroups.
    *   *Lost Information*: Intra-line physical gaps (blocks are merged).
    *   *New Information*: Quantized `typography_class`, contiguous text groupings.
*   **Landmark Stage**:
    *   *Input*: TypographicGroups.
    *   *Output*: `ANCHOR` and `OUTLIER` tokens.
    *   *Lost Information*: **Any typographic transition that is NOT a mathematical peak** (e.g., smaller headers, bold-only shifts, dips into captions). $\leftarrow$ **THIS IS EXACTLY WHERE PAPERLY LOSES THE INFORMATION TO PARSE HEADERS.**
    *   *New Information*: Flags for mathematical maxima.
*   **Semantic Stage**:
    *   *Input*: Groups + Landmark tokens.
    *   *Output*: Semantic AST.
    *   *Lost Information*: None.
    *   *New Information*: Lexical interpretation, hierarchical relationships.

---

## Task 7 — Smallest Possible Architectural Change

The missing information is *typographic transitions that form structural boundaries but aren't mathematical peaks*. 

The smallest possible change to the existing Landmark contract, requiring zero new tokens, zero architectural redesign, and zero changes to Semantic, is to **redefine the mathematical condition for an `OUTLIER` from "Local Maximum" to "Typographic Isolation"**.

**Current Contract (Local Maximum):**
$C_{curr} > C_{prev} \land C_{curr} > C_{next}$
*(Fails to detect headers that are physically smaller than body text).*

**Proposed Contract (Typographic Isolation):**
$C_{curr} \neq C_{prev} \land C_{curr} \neq C_{next}$
*(Detects any block that is typographically distinct from BOTH its preceding and succeeding blocks).*

**Why this works:**
A section header (like "1. INTRODUCTION") is a single group that breaks the typography of the abstract above it, and breaks the typography of the body paragraph below it. By checking $\neq$ instead of $>$, Landmark successfully emits an `OUTLIER` token for maxima, minima, and lateral style shifts (like bolding), while completely ignoring contiguous uniform body text (where $C_{curr} == C_{next}$ evaluates to False).

This extends the existing `OUTLIER` contract perfectly to supply Semantic with exactly the filtering signal it needs, using a single character change in the compiler.
