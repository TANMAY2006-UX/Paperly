# Paperly Semantic Reconstruction Architecture

## Principal Architect Review — Phase 3A.1 Redesign

> **Date:** 2026-07-06
> **Author:** Principal Architect
> **Scope:** Semantic classification engine — full architectural review
> **Status:** GO / NO-GO Decision at end of document

---

## Preamble

I have studied the following before writing this review:

- [classifier.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/classifier.py) — the current semantic classifier (258 lines)
- [publishers.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/publishers.py) — the current publisher detection (115 lines)
- [models.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/models.py) — the data models (185 lines)
- [corpus.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/corpus.py) — corpus statistics (122 lines)
- [ordering.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/ordering.py) — reading order (87 lines)
- [consensus.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/consensus.py) — layout consensus (92 lines)
- [cli.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/cli.py) — pipeline orchestration (138 lines)
- [phase_3_document_understanding_architecture.md](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/docs/phase3/phase_3_document_understanding_architecture.md) — original architecture spec
- [extraction_challenges.md](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/docs/phase3/extraction_challenges.md) — known failure modes
- [heuristics_library_design.md](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/docs/phase3/heuristics_library_design.md) — designed heuristic system
- [semantic_invariants.md](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/docs/phase3/semantic_invariants.md) — semantic invariants
- Your detailed observations on ACM (1-col, 2-col, 3-col, old-style), arXiv, USENIX, CVPR formats
- The 26 papers in the corpus

I did not skim. I read every line.

What follows is honest architectural analysis. Some of it will be uncomfortable.

---

## Question 1: Is the Current Single Semantic Classifier Fundamentally Flawed?

### Verdict: **Yes. Fundamentally flawed. Not salvageable.**

### The Structural Defect

The current [classifier.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/classifier.py) is a **finite state machine** with five states:

```
PREAMBLE → AUTHOR_ZONE → AFFILIATION_ZONE → ABSTRACT_ZONE → KEYWORD_ZONE → BODY
```

This state machine processes blocks **sequentially** in reading order and makes **irrevocable transitions**. Once it enters `AUTHOR_ZONE`, it cannot go back to `PREAMBLE`. Once it enters `ABSTRACT_ZONE`, it cannot reconsider what it classified as `AUTHORS`.

This design encodes a single implicit assumption:

> **Every research paper follows the same front-matter ordering: Title → Authors → Affiliations → Abstract → Keywords → Body.**

This is false.

Your own observations prove it:

| Format | Actual Front-Matter Order |
|---|---|
| ACM 1-col | Title → Authors → *no label* Abstract → CCS Concepts → General Terms → Keywords → ACM Reference → Introduction |
| ACM 2-col | Title → Authors → (sometimes company) → Two-column body immediately |
| ACM old-style | Title (right-aligned) → Authors (right) → Abstract paragraph → Two-column body |
| ACM 3-col (BBR) | Completely different — article-style, light abstract, mixed columns |
| arXiv | Title → Authors → University info → **explicit "Abstract" heading** → Introduction |
| USENIX | **Cover page** → Proceedings page → Then normal paper structure |
| CVPR | Title → Authors → Affiliation → Abstract → Two-column body |

The state machine fails because:

1. **State ordering is wrong for some formats.** ACM 1-col has CCS Concepts between Abstract and Keywords. The classifier has no state for CCS. It either absorbs CCS into ABSTRACT (wrong) or falls through to BODY (wrong).

2. **State transitions are fragile.** The transition from `AUTHOR_ZONE` to `ABSTRACT_ZONE` happens when a block has ≥ 40 words and "looks like prose." But in ACM 1-col, the abstract has no heading — it is just a paragraph. The classifier must somehow distinguish "this prose is the abstract" from "this prose is the first body paragraph," with zero structural signal.

3. **The classifier has no memory.** It cannot look ahead. It cannot say "I see that `1. Introduction` appears 12 blocks from now, therefore everything between authors and `1. Introduction` is front-matter." It processes block-by-block in a single pass with no lookahead.

4. **Recovery is impossible.** If the classifier misclassifies the title — which happens with BBR where "practice" becomes TITLE — every subsequent classification is wrong because the state machine's anchor point is corrupted.

5. **The heuristic count is exploding.** The classifier is 258 lines and already contains 18 invariants (per [semantic_invariants.md](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/docs/phase3/semantic_invariants.md)). Each new paper adds more rules. Each rule interacts with every other rule. This is **O(n²) complexity in heuristic interactions** — the textbook definition of an unmaintainable system.

### Why It Cannot Be Salvaged

The classifier's flaw is not in its individual heuristics. The heuristics are thoughtful. The flaw is in the **architecture** — the assumption that a single sequential pass with a single state machine can handle all document families.

You cannot fix this by adding more states or more heuristics. You would need:
- A CCS_CONCEPTS state for ACM
- A COVER_PAGE state for USENIX
- A PROCEEDINGS_METADATA state for USENIX
- An IMPLICIT_ABSTRACT state for papers without an "Abstract" heading
- A COMPANY_AFFILIATION state for industry papers

Each new state multiplies the number of possible transitions. A 10-state machine has 90 possible transitions. You would need to validate every one of them against every document family. This is a combinatorial explosion.

**The classifier does not need more heuristics. It needs a different architecture.**

---

## Question 2: Should Semantic Reconstruction Happen After Document Family Detection?

### Verdict: **Yes, but with a critical nuance.**

### The Case For: Family-First Parsing

Your observation is correct: humans do not parse papers block-by-block. When a human sees an arXiv paper, they immediately recognize:

- Single column
- LaTeX Computer Modern font
- "Abstract" heading is explicit
- Section numbers are Arabic numerals
- No publisher boilerplate at the top

This recognition happens **before** they read a single word. It is a visual pattern match on the document's **gestalt** — its overall shape, typography, and structural rhythm.

The current pipeline does not do this. It detects the publisher (via string matching in [publishers.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/publishers.py)), but the publisher is barely used. The `PublisherProfile` has `expected_columns`, `has_mixed_layout`, `header_patterns`, and `section_numbering` — but the semantic classifier does not consult any of them. The publisher detection and the semantic classification are effectively decoupled.

**Family-first parsing means:** identify the document family, then apply family-specific parsing rules. This converts a single O(n²)-complex classifier into multiple O(n)-complex parsers, each handling one family.

### The Case Against: Over-Specification

Here is where I challenge your proposal.

Your proposed architecture:

```
PDF → Geometry → Layout Detection → Document Family Detection → Template Selection → Template-specific Semantic Parser → Universal Semantic Tree
```

has a hidden danger: **template rigidity.**

If you define "ACM 1-col" as a template with a fixed slot ordering (Title → Authors → Abstract → CCS → Keywords → Introduction), you are embedding the assumption that every ACM 1-col paper follows this exact ordering. But your own observations show that even within ACM 1-col, there is variation:

- Some have "General Terms" between CCS and Keywords. Some do not.
- Some have "ACM Reference Format" before Introduction. Some do not.
- The 2012 Spanner paper and the 2023 Teaching Ethics paper have different ACM styles — the ACM format itself has evolved over decades.

**If you hardcode templates too rigidly, you reproduce the state machine problem at a higher level of abstraction.** Instead of one brittle state machine, you get N brittle templates.

### The Correct Middle Path

The correct architecture is **family-guided parsing, not template-driven parsing.**

The distinction:

| Template-Driven | Family-Guided |
|---|---|
| "ACM 1-col has exactly these slots in exactly this order" | "ACM 1-col papers tend to have these features with these typographic signatures" |
| Rigid slot ordering | Flexible feature detection |
| Fails when a slot is missing or reordered | Gracefully handles variation within a family |
| Template = prescription | Family = set of priors |

A family does not dictate what must exist. A family provides **prior probabilities** that make ambiguous signals resolvable.

Example: A block on page 1, after the title, with font size equal to body size and no explicit heading — is it the abstract or the first body paragraph?

- Without family context: **ambiguous.** The classifier guesses.
- With family context (ACM 1-col): **almost certainly the abstract,** because ACM 1-col papers always place an unlabeled abstract paragraph immediately after the authors.
- With family context (arXiv): **almost certainly not the abstract,** because arXiv papers always have an explicit "Abstract" heading.

**The family does not classify the block. The family disambiguates the evidence.**

---

## Question 3: How Should Document Family Detection Work?

### The Ideal Detector: Multi-Signal Evidence Fusion

Document family detection must be robust. If it misidentifies the family, every downstream parser receives incorrect priors. Therefore, the detector must use **multiple independent signals** and fuse them with confidence scoring.

### Signal Categories (Ordered by Reliability)

#### Tier 1: High-Reliability Signals (Confidence 0.8–1.0 each)

**1. Publisher Strings**
Explicit text markers that unambiguously identify the publisher:
- `"Permission to make digital or hard copies"` → ACM (100% reliable)
- `"Advances in Neural Information Processing Systems"` → NeurIPS
- `"arXiv:"` followed by identifier pattern → arXiv preprint
- `"USENIX Association"` → USENIX
- `"IEEE"` + `"978-1-"` → IEEE proceedings
- `"CVPR"` or `"IEEE Conference on Computer Vision"` → CVPR

These are the most reliable signals because they are **self-declared** by the publisher.

**2. Copyright/License Blocks**
Footer or first-page blocks containing copyright statements:
- `"© 20xx ACM"` → ACM
- `"Licensed under a Creative Commons"` + arXiv identifier → arXiv
- `"Authorized licensed use limited to"` → IEEE

#### Tier 2: Medium-Reliability Signals (Confidence 0.4–0.7 each)

**3. Page Structure Fingerprint**
The geometric arrangement of blocks on page 1:
- Title in top 30%, full-width, followed by centered author block, followed by explicit "Abstract" → arXiv-like
- Title in top 20%, followed by 2-column body starting on page 1 → ACM/IEEE 2-col
- First page with very little content, dominated by conference name and author list → USENIX cover page
- Title right-aligned with author block right-aligned → ACM old-style

**4. Column Layout**
Already computed by the frozen Phase 3A.0 pipeline:
- Single column → arXiv, NeurIPS, ACM 1-col
- Double column → ACM 2-col, IEEE, CVPR, USENIX (body pages)
- Mixed (page 1 single, rest double) → Common in ACM, IEEE

**5. Font Fingerprint**
The dominant font family provides a strong signal:
- Computer Modern Roman variants → LaTeX, likely arXiv/NeurIPS
- Times/Nimbus Roman → ACM, IEEE
- Palatino → Some Springer journals
- Helvetica/Arial headings → Nature, MDPI

**6. Section Numbering Style**
Detected from the first few section headings:
- Arabic numerals (`1.`, `2.`, `3.1`) → Most modern conferences
- Roman numerals (`I.`, `II.`, `III.`) → IEEE Transactions, some classical
- Unnumbered bold headings → Nature, some journal articles

#### Tier 3: Low-Reliability Signals (Confidence 0.1–0.3 each)

**7. PDF Metadata**
`doc.metadata["creator"]`, `doc.metadata["producer"]`:
- `"LaTeX with hyperref"` → academic paper (not publisher-specific)
- `"Adobe InDesign"` → journal/magazine layout
- `"Microsoft Word"` → unusual for CS papers, possibly industry report

**8. Page Dimensions**
- US Letter (612 × 792) → common in US conferences
- A4 (595 × 842) → common in European venues
- Not diagnostic on its own, but provides weak evidence

### Fusion Algorithm

The detector should **not** use if-else cascading (which is what [publishers.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/publishers.py) does today). Instead:

1. **Collect all signals** independently. Each signal returns a list of `(family_name, confidence)` tuples.
2. **Aggregate per family.** For each candidate family, sum the weighted confidences from all supporting signals.
3. **Select the family** with the highest aggregated confidence, provided it exceeds a minimum threshold (e.g., 0.50).
4. **If no family exceeds threshold**, classify as `UNKNOWN` and fall back to the generic parser.
5. **Log every signal** that contributed to the decision, with its individual confidence, for debugging.

### What a "Family" Represents

A family is **not** a publisher name. A family is a **layout archetype.** The set of families I recommend:

| Family ID | Description | Column Layout | Abstract Style | Section Style |
|---|---|---|---|---|
| `ARXIV_SINGLE` | Standard arXiv/NeurIPS single-column | 1 | Explicit heading | Arabic numbered |
| `ACM_SINGLE` | ACM single-column (Spanner, BigTable era) | 1 | Implicit (no heading) | ALL-CAPS, sometimes numbered |
| `ACM_DOUBLE` | ACM two-column (Dynamo, GFS era) | 2 | Varies | Bold, numbered |
| `ACM_MODERN` | Modern ACM (post-2017 template) | 1 or 2 | Explicit or implicit | Varies |
| `IEEE_DOUBLE` | IEEE Transactions/Conference | 2 | Explicit heading | Roman or Arabic numbered |
| `USENIX_PROCEEDINGS` | USENIX with cover page | 2 (after cover) | Explicit heading | Arabic numbered |
| `CVPR_DOUBLE` | CVPR/ICCV/ECCV proceedings | 2 | Explicit heading | Arabic numbered |
| `SPRINGER_SINGLE` | Springer LNCS / journal | 1 | Explicit heading | Arabic numbered |
| `NATURE_SINGLE` | Nature/Science family | 1 or 2 | Explicit heading | Unnumbered bold |
| `GENERIC` | Unknown / fallback | Detected | Best-effort | Best-effort |

> [!IMPORTANT]
> These families are **not publisher names**. `ACM_SINGLE` and `ACM_MODERN` are different families even though they are both ACM. A family is defined by its layout archetype, not by who published it.

---

## Question 4: One Parser or Many Small Parsers?

### Verdict: **Many small parsers, but with a shared skeleton.**

### The Argument for Many Parsers

A single universal parser with 15 families embedded as branches would quickly become the same tangled state machine you have today, just wrapped in a bigger function. Separate files provide:

1. **Isolation.** A bug fix in `acm_single.py` cannot break `arxiv_single.py`.
2. **Testability.** Each parser has its own test corpus.
3. **Readability.** A developer debugging Spanner (ACM single-column) opens one file, not a 1000-line monolith.
4. **Independent evolution.** When ACM changes their template (they do, every few years), only `acm_modern.py` changes.

### The Argument Against Naive Separation

If each parser is completely independent — `arxiv_parser.py`, `acm_parser.py`, `usenix_parser.py` — you will have massive code duplication. All parsers need to:

- Detect section headings (the algorithm differs slightly by family, but the core logic is shared)
- Detect figure/table captions (identical across all families)
- Detect the references section (identical)
- Handle footnotes (mostly identical)
- Assemble content into sections (identical)

If you duplicate this logic across 10 parsers, every bug fix must be applied 10 times. This is worse than the current architecture.

### The Correct Design: Strategy Pattern with Shared Infrastructure

The architecture should have:

1. **A shared `SemanticEngine`** that handles universal operations:
   - Section heading detection (with configurable numbering style)
   - Figure/table caption detection
   - References section detection
   - Footnote detection
   - Content assembly

2. **Family-specific `FrontMatterStrategy` implementations** that handle only the front-matter parsing:
   - Title detection (position and typography vary by family)
   - Author/affiliation parsing (structure varies dramatically)
   - Abstract detection (explicit vs. implicit, labeled vs. unlabeled)
   - Keywords/CCS/General Terms (ACM-specific)
   - Cover page handling (USENIX-specific)

3. **Family-specific `BodyHints`** that adjust the shared engine:
   - Section numbering style (Arabic vs. Roman)
   - Heading typography (Bold vs. ALL-CAPS vs. Small-caps)
   - Expected heading hierarchy depth (1 level vs. 3 levels)

This gives you 10 small strategy files (one per family) plus one robust shared engine, instead of 10 large duplicated parsers.

---

## Question 5: Should There Be a Universal Semantic Grammar?

### Verdict: **Absolutely yes. This is non-negotiable.**

Every parser — regardless of family — must output the same semantic tree. If parsers output different structures, the renderer must handle N different formats. This defeats the purpose of having multiple parsers.

### The Canonical Semantic Types

```
DOCUMENT
├── TITLE
├── AUTHORS
│   └── AUTHOR (one per person)
│       └── AFFILIATION (optional)
├── ABSTRACT
├── KEYWORDS (optional)
├── FRONT_MATTER (catch-all for CCS, General Terms, ACM Reference, etc.)
├── SECTION (recursive)
│   ├── HEADING
│   ├── PARAGRAPH
│   ├── FIGURE_REF (placeholder)
│   ├── TABLE_REF (placeholder)
│   ├── EQUATION_REF (placeholder)
│   └── SECTION (sub-section, recursive)
├── ACKNOWLEDGEMENTS (optional)
├── REFERENCES
│   └── REFERENCE_ITEM
├── APPENDIX (optional, recursive like SECTION)
├── FIGURE
│   └── CAPTION
├── TABLE
│   └── CAPTION
├── EQUATION
├── FOOTNOTE
└── NOISE (explicitly classified, never rendered)
```

### Critical Design Rules

1. **Every parser must produce exactly this tree structure.** No parser may invent new types. If a parser encounters something it cannot classify, it uses `FRONT_MATTER` (if before body) or `PARAGRAPH` (if during body).

2. **The tree is the contract.** Everything upstream of the tree (parsing) can change. Everything downstream (rendering, search, export) depends only on the tree. The tree is the **interface boundary** between extraction and presentation.

3. **NOISE is an explicit classification.** A block classified as NOISE was examined and rejected. This is different from an unclassified block. NOISE blocks are never rendered but are preserved in the audit log.

4. **FRONT_MATTER is the preamble catch-all.** CCS Concepts, General Terms, ACM Reference Format, conference metadata — anything that appears between KEYWORDS and the first SECTION and does not fit another type. The renderer may display these in a collapsed metadata section or ignore them entirely.

---

## Question 6: Where Should Text Cleanup Occur?

### Verdict: **Before semantic parsing. Unconditionally.**

### The Reasoning

Text cleanup must happen at the earliest possible stage because every downstream consumer benefits from clean text. If cleanup happens after semantic parsing, you must:

- Parse dirty text (harder — ligatures break word boundary detection)
- Clean text after parsing (requires touching every semantic node)
- Risk that cleanup changes affect classification (e.g., a ligature in "ﬁgure" preventing a regex match on "figure")

### The Cleanup Stack (Applied in This Order)

1. **Unicode Normalization (NFC).** Converts composed characters to their canonical form. This ensures that "é" (U+00E9) and "e" + combining accent (U+0065 U+0301) are identical.

2. **Ligature Decomposition.** `ﬁ → fi`, `ﬂ → fl`, `ﬀ → ff`, `ﬃ → ffi`, `ﬄ → ffl`. This is already partially implemented in [normalize.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/normalize.py).

3. **Broken Apostrophe Repair.** Some PDFs produce `don' t` (space before `t`) or use the wrong Unicode character for apostrophes. Normalize to U+2019 (RIGHT SINGLE QUOTATION MARK) or ASCII apostrophe.

4. **Soft Hyphen Removal.** U+00AD (SOFT HYPHEN) is invisible but present in some PDFs. Remove unconditionally.

5. **Line-Wrap Hyphen Repair.** This is the only cleanup that requires context:
   - If a block ends with `-` and the next block in reading order starts with a lowercase letter → **join without the hyphen** (e.g., `"distri-"` + `"buted"` → `"distributed"`).
   - If the block ends with `-` and the next starts with an uppercase letter → **preserve the hyphen** (it is a real hyphen, e.g., `"peer-"` + `"to-peer"` is wrong, but `"well-"` + `"Known"` is a line break at a hyphen).
   - This must be conservative. A false join (`"non-"` + `"trivial"` → `"nontrivial"`) is worse than a missed join.

6. **Whitespace Normalization.** Collapse multiple spaces to single spaces. Trim leading/trailing whitespace. Normalize line breaks.

### Where in the Pipeline

These cleanups belong in the existing normalization stage (Stage 2 in the frozen pipeline, currently [normalize.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/normalize.py)). They modify the `TextBlock.text` field before any semantic analysis begins.

> [!WARNING]
> Line-wrap hyphen repair (step 5) requires reading order, which is computed in Stage 4 (after normalization). This creates a dependency conflict. Two options:
>
> **Option A:** Perform steps 1–4 in Stage 2. Defer step 5 to a post-ordering cleanup pass after Stage 4.
>
> **Option B:** Perform all cleanups in a dedicated Stage 4.5 after reading order is established.
>
> **Recommendation:** Option A. Steps 1–4 are character-level and context-free. Step 5 is the only one that requires document context. Splitting them is cleaner than delaying everything.

---

## Question 7: How Would I Design the World's Best Research Paper Parser?

### The Architecture I Would Build

If I were designing the world's best deterministic research paper parser from scratch, here is what I would build. Not what is easiest. What is correct.

### The Pipeline

```
PDF File
    │
    ▼
┌──────────────────────────────────┐
│  FROZEN LAYERS (Phase 3A.0)      │
│                                  │
│  Stage 1: Ingestion              │
│  Stage 2: Block Extraction       │
│  Stage 3: Layout Analysis        │
│  Stage 4: Reading Order          │
│  Stage 4b: Layout Consensus      │
│  Corpus Statistics               │
│                                  │
│  Output: Ordered TextBlock list  │
│          DocumentLayout          │
│          DocumentCorpus          │
│          LayoutProfile per page  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  NEW: Stage 5 — Text Cleanup     │
│                                  │
│  Unicode NFC                     │
│  Ligature decomposition          │
│  Apostrophe repair               │
│  Soft hyphen removal             │
│  Whitespace normalization        │
│                                  │
│  Output: Cleaned TextBlock list  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  NEW: Stage 6 — Noise Removal    │
│                                  │
│  Running header removal          │
│  Page number removal             │
│  Publisher boilerplate removal   │
│  Watermark removal               │
│                                  │
│  Output: Filtered TextBlock list │
│          (noise blocks flagged)  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  NEW: Stage 7 — Landmark         │
│  Detection                       │
│                                  │
│  Detect structural anchors:      │
│  • "Abstract" / "ABSTRACT"       │
│  • "1. Introduction" / "I."      │
│  • "References" / "Bibliography" │
│  • "Acknowledgements"            │
│  • "Appendix"                    │
│  • Figure/Table caption prefixes │
│                                  │
│  These are HIGH-CONFIDENCE       │
│  anchors. They partition the     │
│  document into zones.            │
│                                  │
│  Output: Landmark list +         │
│          Zone boundaries         │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  NEW: Stage 8 — Family           │
│  Detection                       │
│                                  │
│  Multi-signal evidence fusion:   │
│  • Publisher strings             │
│  • Copyright blocks              │
│  • Page structure fingerprint    │
│  • Column layout                 │
│  • Font fingerprint              │
│  • Section numbering style       │
│  • PDF metadata (weak)           │
│                                  │
│  Output: DocumentFamily +        │
│          FamilyConfidence         │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  NEW: Stage 9 — Front-Matter     │
│  Parsing (Family-Guided)         │
│                                  │
│  Dispatches to family strategy:  │
│  • arxiv_single_strategy         │
│  • acm_single_strategy           │
│  • acm_double_strategy           │
│  • ieee_double_strategy          │
│  • usenix_strategy               │
│  • cvpr_strategy                 │
│  • generic_strategy (fallback)   │
│                                  │
│  Each strategy classifies:       │
│  TITLE, AUTHORS, AFFILIATIONS,   │
│  ABSTRACT, KEYWORDS,             │
│  FRONT_MATTER                    │
│                                  │
│  Uses landmarks as anchors.      │
│  Uses family priors to resolve   │
│  ambiguity.                      │
│                                  │
│  Output: Classified front-matter │
│          blocks                  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  NEW: Stage 10 — Body Parsing    │
│  (Shared Engine)                 │
│                                  │
│  Runs after front-matter, using  │
│  landmarks as boundaries:        │
│                                  │
│  • Section heading detection     │
│    (configurable numbering       │
│     style from family)           │
│  • Body paragraph classification │
│  • Figure/Table caption detection│
│  • Footnote detection            │
│  • Equation detection            │
│  • Reference item detection      │
│    (after References landmark)   │
│                                  │
│  Output: Fully classified        │
│          SemanticBlock list       │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  NEW: Stage 11 — Hyphen Repair   │
│                                  │
│  Now that reading order AND       │
│  semantic types are known:       │
│  • Join line-broken words        │
│  • Merge fragmented paragraphs   │
│  • Only within PARAGRAPH and     │
│    ABSTRACT blocks               │
│  • Never across section          │
│    boundaries                    │
│                                  │
│  Output: Repaired text content   │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Stage 12 — Tree Assembly        │
│                                  │
│  Build the universal semantic    │
│  tree from classified blocks.    │
│  Stitch sections. Nest           │
│  subsections. Attach figures     │
│  and tables to nearest sections. │
│                                  │
│  Output: SemanticDocument        │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Stage 13 — Validation           │
│                                  │
│  Structural invariants:          │
│  • Exactly 1 TITLE               │
│  • At least 1 AUTHOR             │
│  • At least 1 SECTION            │
│  • No BODY text before ABSTRACT  │
│  • No orphan blocks              │
│                                  │
│  Confidence scoring:             │
│  • Average classification        │
│    confidence                    │
│  • Family detection confidence   │
│  • Landmark coverage ratio       │
│                                  │
│  Output: Validated               │
│          SemanticDocument +      │
│          QualityReport           │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  Stage 14 — JSON Export          │
│                                  │
│  Serialize to Paperly JSON       │
│  schema. Embed quality report.   │
│  Write audit log.                │
│                                  │
│  Output: paper.json              │
│          paper_audit.log         │
└──────────────────────────────────┘
```

### The Key Insight: Landmarks Before Classification

The most important architectural decision in this pipeline is **Stage 7: Landmark Detection.**

Landmarks are the document's **structural skeleton.** They are the blocks that a human would identify first when scanning a paper:

- The word "Abstract" (or "ABSTRACT")
- The first numbered section heading ("1. Introduction" or "1 INTRODUCTION")
- The word "References" (or "BIBLIOGRAPHY")

These landmarks are **high-confidence, publisher-independent, and position-independent.** They can be detected with simple text matching. They do not require font analysis or page position heuristics.

Once landmarks are detected, they **partition the document into zones:**

- Everything before "Abstract" → front-matter zone (title, authors, affiliations)
- "Abstract" to first section heading → abstract zone
- First section to "References" → body zone
- "References" to end → references zone

This partitioning is **the single most valuable operation in the pipeline** because it constrains every subsequent classification. The front-matter parser only needs to handle blocks in the front-matter zone. The body parser only processes the body zone. Neither can accidentally consume blocks from the wrong zone.

**This is what the current classifier lacks.** It has no landmarks. It processes blocks sequentially with no global awareness of the document's structure. It is navigating a city street-by-street without a map.

---

## Question 8: Would This Architecture Scale to 500,000 Papers?

### Analysis

At 500,000 papers, the following pressures emerge:

| Concern | Risk | Mitigation |
|---|---|---|
| **Family coverage** | New publishers will appear that match no existing family | `GENERIC` family must be robust enough to handle unknowns at 70%+ quality |
| **Family evolution** | ACM's template has changed 4 times since 2000. The ACM of 2030 may look different. | Families are identified by geometric fingerprint, not publisher name. A new ACM template creates a new family variant. |
| **Performance** | 500K × 14-stage pipeline | Each stage is O(n) in page count. No stage requires cross-document state. Parallelizable. |
| **Maintenance** | Bug fixes in shared engine propagate instantly; family strategies evolve independently | Strategy pattern isolates family-specific logic |
| **Regression** | A fix for one family breaks another | Per-family regression suites prevent cross-contamination (see Question 10) |
| **Storage** | 500K JSON files, each 50–500 KB | ~50 GB. Trivial. |

### What Would Cause Scaling Failure

1. **If family detection requires human intervention for new families.** This is the biggest risk. If every new publisher requires a developer to create a new strategy file, the system does not scale. The `GENERIC` family must handle 80%+ of unknown papers automatically.

2. **If the landmark vocabulary is too narrow.** If landmarks only recognize English headings ("Abstract", "References"), the system fails on non-English papers. The landmark vocabulary must be extensible.

3. **If per-paper overrides become the norm.** If 30% of papers need `paper_config.json` overrides, you have not automated parsing — you have built a semi-automated system with a config-file escape hatch. The goal is < 5% override rate.

### Future-Proofing Changes to Make Today

1. **Make the family registry data-driven, not code-driven.** Families should be defined in a declarative format (YAML/JSON), not as Python classes. This allows adding new families without writing code.

2. **Make the landmark vocabulary configurable.** Store landmark patterns in a data file, not as hardcoded regex in Python.

3. **Build the quality report into the output from day one.** Every parsed paper should carry a `quality_score` (0.0–1.0) computed from classification confidences. This enables automated triage: papers with quality < 0.7 are flagged for human review.

4. **Build the audit log as a first-class output, not a debug afterthought.** The audit log should be structured JSON, not printf-style strings. It should be queryable: "show me every paper where TITLE confidence was below 0.8."

---

## Question 9: How Should Paperly Continuously Improve?

### The Adaptive Loop

When a completely new publisher appears, you do NOT want to:
- Write a new parser
- Add new regex patterns
- Create a `corrections.json`

Instead, the system should:

### Tier 1: Automatic Adaptation (No Human)

1. **Family detection fails gracefully.** The unknown paper falls through to `GENERIC` family.
2. **`GENERIC` strategy uses landmark-based parsing.** It finds "Abstract", finds "1. Introduction", finds "References", and partitions accordingly. No family-specific priors. Pure structural detection.
3. **The quality report flags low confidence.** The paper is parsed, but the quality score is 0.6 instead of 0.9. The system does not refuse to parse — it parses with degraded confidence.

### Tier 2: Guided Improvement (Minimal Human Input)

4. **A developer reviews the low-confidence paper.** They notice that the title was missed because the font size was only 1.1× body (below the 1.4× threshold).
5. **They create a new family definition** — not by writing a parser, but by defining a family profile in YAML:

```yaml
family_id: MDPI_SINGLE
description: "MDPI journal single-column format"
signals:
  publisher_strings: ["MDPI", "mdpi.com"]
  column_layout: 1
  font_fingerprint: ["Palatino"]
priors:
  title_size_ratio: 1.1  # smaller than default
  abstract_style: explicit  # has "Abstract" heading
  section_numbering: arabic
  heading_style: bold_numbered
```

6. **This YAML file is all that is needed.** The shared engine uses the priors from this profile. No new Python code is written.

### Tier 3: Structural Improvement (Developer Required)

7. **If the new publisher has a fundamentally different front-matter structure** (e.g., the abstract appears AFTER the introduction, or the paper has no sections at all — just continuous prose), then a new strategy file is needed.
8. **This should be rare.** 95%+ of academic papers follow the Title → Authors → Abstract → Sections → References structure. The only common exception is the USENIX cover page pattern, which is already handled.

### What This Means in Practice

For Paperly to handle MDPI, Springer, Elsevier, Nature, ICML, ICLR, ACL, NAACL, EMNLP — you do NOT need 15 parsers. You need:

- **3–4 strategy files** (arXiv-like, ACM-like, IEEE-like, USENIX-like) that cover 90% of papers
- **1 generic fallback** that handles the remaining 10% with landmarks only
- **YAML family profiles** that adjust priors for specific publishers within each strategy group

Most of your target list (ICML, ICLR, ACL, NAACL, EMNLP, NeurIPS) use the arXiv-like template. They are single-column, LaTeX-generated, with explicit "Abstract" headings and Arabic-numbered sections. One strategy covers all of them. The family profiles differ only in publisher strings and minor typography.

---

## Question 10: How Should Every Semantic Parser Be Validated?

### The Validation Pyramid

```
                    ┌─────────────┐
                    │  Visual     │
                    │  Diffing    │   ← Manual: "Does this look right?"
                    ├─────────────┤
                    │  Semantic   │
                    │  Invariants │   ← Automated: structural truth assertions
                    ├─────────────┤
                    │  Golden     │
                    │  Dataset    │   ← Automated: block-level ground truth
                    ├─────────────┤
                    │  Regression │
                    │  Suite      │   ← Automated: output stability
                    ├─────────────┤
                    │  Unit Tests │   ← Automated: heuristic correctness
                    └─────────────┘
```

### Layer 1: Unit Tests (Per Heuristic)

Every heuristic gets its own test file. Tests are synthetic — they create `TextBlock` objects with known properties and assert that the heuristic fires or does not fire.

Coverage requirement: every heuristic must have:
- 3+ positive cases (heuristic correctly fires)
- 3+ negative cases (heuristic correctly does not fire)
- 1+ edge case from the actual corpus

### Layer 2: Regression Suite (Per Paper)

For every paper in the corpus, store a **snapshot** of the semantic classification output. The snapshot is a JSON file listing every block and its classification:

```json
{
  "paper": "spanner",
  "family": "ACM_SINGLE",
  "snapshot_version": "2026-07-06",
  "blocks": [
    {"block_num": 0, "page": 0, "text_prefix": "Spanner: Google's", "type": "TITLE", "confidence": 0.95},
    {"block_num": 1, "page": 0, "text_prefix": "James C. Corbett", "type": "AUTHORS", "confidence": 0.90},
    ...
  ]
}
```

**Before every commit,** the regression suite re-parses every corpus paper and compares the output to the stored snapshot. Any change in classification triggers a diff report. The developer must explicitly approve changes (by updating the snapshot) or fix the regression.

This is the **single most important validation mechanism.** It prevents the "fix one paper, break another" problem that plagues the current classifier.

### Layer 3: Golden Dataset (Block-Level Ground Truth)

For **5 representative papers** (one per major family), create a **human-verified ground truth file** where every block is manually labeled with its correct semantic type. This is the source of truth for measuring classification accuracy.

Recommended golden papers:
- Attention Is All You Need (arXiv single-column)
- Spanner (ACM single-column)
- Dynamo (ACM two-column)
- In Search of an Understandable Consensus Algorithm (USENIX)
- Deep Residual Learning / ResNet (CVPR)

Accuracy is measured as: `correctly classified blocks / total blocks`.

Target: **≥ 95% accuracy** on golden papers. ≥ 85% on non-golden corpus papers.

### Layer 4: Semantic Invariants (Structural Truth Assertions)

These are boolean assertions that must hold for EVERY parsed paper, regardless of family:

1. **Exactly one TITLE.** (If zero: parser failed. If multiple: parser confused.)
2. **At least one AUTHORS block.**
3. **At most one ABSTRACT.**
4. **TITLE appears before AUTHORS.** (In reading order.)
5. **AUTHORS appears before ABSTRACT.** (In reading order.)
6. **ABSTRACT appears before first SECTION.** (In reading order.)
7. **REFERENCES appears after all SECTION blocks.** (In reading order.)
8. **No BODY_TEXT classified as TITLE, AUTHORS, or ABSTRACT.** (Invariant 18 from current spec.)
9. **No block is unclassified.** Every block is either a semantic type or NOISE.
10. **All blocks in the output are present in the input.** (Pure permutation — no blocks created or destroyed.)
11. **Total word count of output ≥ 90% of total word count of input minus noise.** (We should not be losing content.)

These invariants are checked automatically after every parse. Any violation is a hard failure.

### Layer 5: Visual Diffing (Human Review)

For new papers or papers with low quality scores, generate a **visual diff overlay:**

- Render the original PDF page as an image
- Overlay colored rectangles showing the semantic classification of each block:
  - Green = TITLE
  - Blue = AUTHORS
  - Yellow = ABSTRACT
  - Orange = SECTION_HEADING
  - Gray = NOISE
  - Red = unclassified or low-confidence

The existing [debug.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/debug.py) already generates debug overlays. Extend it to show semantic classifications.

A human reviews the visual diff and confirms correctness. This is the final validation gate before a paper is added to the corpus.

---

## Question 11: How Should Unknown Papers Behave?

### The Graceful Degradation Ladder

When Paperly encounters a paper whose layout has never been seen:

**Step 1: Family detection returns `GENERIC` with low confidence.**
The detector could not match any known family. Confidence is below 0.50. The paper is flagged as unknown.

**Step 2: The `GENERIC` strategy parses using landmarks only.**
It finds structural anchors:
- "Abstract" → marks abstract zone
- First numbered heading → marks body start
- "References" → marks references zone

If landmarks are found, the parsing quality is decent — perhaps 80% accuracy. The title is the largest text on page 1. Authors are between the title and abstract. Sections are detected by bold + numbered text.

**Step 3: If no landmarks are found, use geometric heuristics only.**
- Title = largest text block on page 1 in the top 30%
- Abstract = first substantial prose block (≥ 40 words) before the first section heading
- Section headings = bold blocks that start with numbers
- Everything else = PARAGRAPH

This produces ~60% accuracy. Sections are probably correct. Title is probably correct. Authors and abstract are uncertain.

**Step 4: The quality report records degraded confidence.**
```json
{
  "quality_score": 0.62,
  "family": "GENERIC",
  "family_confidence": 0.30,
  "warnings": [
    "No publisher strings detected",
    "Abstract detected by position only (no 'Abstract' heading found)",
    "Author block confidence below 0.7"
  ]
}
```

**Step 5: The renderer still displays the paper.**
The reading experience is functional but imperfect. The title is shown. The abstract is shown (possibly with a warning badge). The body is readable. The paper is usable even if some front-matter is misclassified.

**Step 6: Human review is recommended.**
The low quality score triggers a notification. A developer reviews the visual diff, identifies the family, and either:
- Creates a new family profile (YAML)
- Adds the paper to the regression suite with its correct classifications

### What Must Never Happen

- The parser must **never crash** on an unknown paper. Every code path must produce output.
- The parser must **never produce an empty document**. Even if everything is classified as PARAGRAPH, the paper is readable.
- The parser must **never silently produce wrong output.** If confidence is low, the quality report must say so. Silent incorrectness is worse than a crash.

---

## Question 12: Every Flaw in Your Current Thinking

I am going to assume you are wrong about several things. Here is what I believe you are wrong about, or at least incomplete about.

### Flaw 1: You Are Thinking in Publisher Names, Not Layout Archetypes

Your observations group papers by publisher: "ACM papers do X", "arXiv papers do Y." But your own observations prove that ACM alone has **four different layouts** (1-col, 2-col, old-style, 3-col). "ACM" is not a useful classification unit. The layout archetype is.

This matters because when you encounter a new ACM paper in 2028, it may use a **fifth layout** that matches none of your four. If your system is organized by publisher, you need to modify `acm_parser.py`. If your system is organized by layout archetype, the new paper may match an existing archetype (e.g., "single-column with explicit abstract") and parse correctly without any changes.

**Correction:** Do not name families after publishers. Name them after structural archetypes. The publisher is a detection signal, not an organizational principle.

### Flaw 2: You Are Underestimating the Generic Parser

Your instinct is to create specific parsers for every publisher. But the reality is: **90% of papers in CS share the same structure:** Title → Authors → Abstract → Numbered Sections → References. The variation is in typography and the presence/absence of optional elements (CCS, keywords, acknowledgements).

A well-built generic parser with landmark detection would handle 80%+ of papers correctly without any family-specific logic. The family strategies are needed for the remaining 20% — primarily for front-matter disambiguation in papers without explicit "Abstract" headings.

If you over-invest in family-specific parsers and under-invest in the generic parser, you get a system that works perfectly on known publishers and fails catastrophically on unknown ones. The opposite is safer.

**Correction:** Build the generic parser first. Make it excellent. Then add family strategies only where the generic parser demonstrably fails.

### Flaw 3: You Are Not Accounting for Multi-Page Front-Matter

Your observations describe front-matter as a page 1 phenomenon. But several papers in your corpus have front-matter that spans multiple pages:

- USENIX papers have cover pages (page 1) and proceedings pages (page 2) before the real paper starts on page 3.
- Some ACM papers have a full-page author/affiliation block that pushes the abstract to page 2.
- Long author lists (LLaMA has ~30 authors) can push the abstract to the bottom of page 1 or the top of page 2.

The classifier must not assume that front-matter ends on page 1. It must use landmarks ("Introduction" heading) to determine where front-matter ends, regardless of page number.

**Correction:** Front-matter parsing must be page-agnostic. The boundary is the first section heading, not the page break.

### Flaw 4: You Have Not Considered Papers That Violate the Grammar

Some papers do not have:
- An abstract (rare, but some workshop papers omit it)
- Numbered sections (Nature/Science papers use unnumbered bold headings)
- A references section (some extended abstracts have no references)
- Authors in the traditional sense (some anonymous submission drafts say "Anonymous" or "Under Review")

Your universal grammar must handle absence gracefully. Every field except TITLE should be optional. The parser must not crash or produce garbage when expected elements are missing.

**Correction:** Make the grammar tolerant of missing elements. The only hard requirement is TITLE.

### Flaw 5: You Are Conflating Detection and Classification

Your proposed pipeline has "Template Selection" → "Template-specific Semantic Parser." This implies that family detection happens once, a parser is selected, and that parser runs to completion.

But what if family detection is wrong? What if the paper is classified as ACM_SINGLE but is actually ARXIV_SINGLE? The wrong parser runs, produces incorrect output, and there is no recovery.

**Correction:** Family detection should be verified by the parser. If the parser encounters evidence that contradicts the detected family (e.g., it expects an implicit abstract but finds an explicit "Abstract" heading), it should report the contradiction in the quality report. Optionally, it should retry with the generic parser.

### Flaw 6: You Have Not Addressed the "Teaching Ethics" Problem

Your ACM 1-col papers include "Teaching Ethics in Computing." This paper is a 2023 ACM publication that likely uses the ACM Large format — a different template from the 2012 Spanner paper. ACM has changed their template at least three times:

- Pre-2017: Classic ACM format (Spanner, BigTable)
- 2017–2022: `acmart` v1 format
- 2023+: Updated `acmart` format

If you define "ACM_SINGLE" as a single family, you are lumping together papers with significantly different front-matter structures. You need to either:
- Define sub-families (ACM_SINGLE_CLASSIC, ACM_SINGLE_MODERN)
- Or make the family strategy robust enough to handle both variants

**Correction:** Expect format evolution. Design families to be tolerant of variation within a publisher.

---

## Question 13: The Final Architecture

### Directory Structure

```
extractor/
├── __init__.py
├── __main__.py
│
├── # ─── FROZEN LAYERS (Phase 3A.0) ─────────────────
├── ingest.py              # Stage 1: PDF ingestion
├── normalize.py           # Stage 2: Block extraction + char cleanup
├── layout.py              # Stage 3: Per-page layout detection
├── consensus.py           # Stage 4: Document layout consensus
├── ordering.py            # Stage 4b: Reading order
├── corpus.py              # Corpus statistics
│
├── # ─── NEW LAYERS (Phase 3A.1 Redesign) ──────────
├── cleanup.py             # Stage 5: Text cleanup (NFC, ligatures, hyphens)
├── noise.py               # Stage 6: Noise removal (headers, footers, boilerplate)
├── landmarks.py           # Stage 7: Landmark detection (structural anchors)
├── family_detector.py     # Stage 8: Document family detection (evidence fusion)
├── semantic_engine.py     # Stages 9–10: Semantic classification orchestrator
│
├── families/              # Family strategy implementations
│   ├── __init__.py
│   ├── registry.py        # Family registry + dispatch
│   ├── base_strategy.py   # Abstract base for front-matter strategies
│   ├── generic.py         # GENERIC fallback (landmark-only parsing)
│   ├── arxiv_like.py      # arXiv, NeurIPS, ICML, ICLR, ACL, NAACL, EMNLP
│   ├── acm_classic.py     # ACM pre-2017 (Spanner, BigTable, MapReduce)
│   ├── acm_double.py      # ACM 2-col (Dynamo, GFS, Cassandra)
│   ├── ieee_like.py       # IEEE + BBR + RED + QUIC
│   ├── usenix.py          # USENIX with cover page handling
│   └── cvpr_like.py       # CVPR, ICCV, ECCV
│
├── families/profiles/     # Declarative family profiles (YAML)
│   ├── arxiv_single.yaml
│   ├── neurips_single.yaml
│   ├── acm_single_classic.yaml
│   ├── acm_double_classic.yaml
│   ├── ieee_double.yaml
│   ├── usenix_proceedings.yaml
│   ├── cvpr_double.yaml
│   └── generic.yaml
│
├── body_parser.py         # Stage 10: Body parsing (shared engine)
├── hyphen_repair.py       # Stage 11: Line-wrap hyphen repair
├── tree_assembler.py      # Stage 12: Semantic tree assembly
├── validator.py           # Stage 13: Structural invariant validation
├── exporter.py            # Stage 14: JSON export
│
├── # ─── SUPPORTING ────────────────────────────────
├── models.py              # All dataclass definitions
├── confidence.py          # Confidence thresholds and scoring
├── debug.py               # Visual debug overlay generation
├── cli.py                 # CLI entry point
│
├── # ─── VALIDATION ────────────────────────────────
├── golden/                # Golden dataset (human-verified block labels)
│   ├── attention.golden.json
│   ├── spanner.golden.json
│   ├── dynamo.golden.json
│   ├── raft.golden.json
│   └── resnet.golden.json
│
└── snapshots/             # Regression snapshots (auto-generated)
    ├── attention.snapshot.json
    ├── spanner.snapshot.json
    ├── ...
    └── (one per corpus paper)
```

### Pipeline Stages

| Stage | Module | Input | Output | Frozen? |
|---|---|---|---|---|
| 1 | `ingest.py` | PDF file | `ExtractionContext` with raw `PageBlocks` | ✓ |
| 2 | `normalize.py` | Raw blocks | Normalized `TextBlock` list (unit coords) | ✓ |
| 3 | `layout.py` | Normalized blocks | `LayoutProfile` per page | ✓ |
| 4 | `consensus.py` | Page layouts | `DocumentLayout` (single/double/hybrid) | ✓ |
| 4b | `ordering.py` | Blocks + layout | Ordered `TextBlock` list | ✓ |
| C | `corpus.py` | All blocks | `DocumentCorpus` (body font, title font, headers) | ✓ |
| 5 | `cleanup.py` | Ordered blocks | Cleaned text (NFC, ligatures, apostrophes, soft hyphens) | **New** |
| 6 | `noise.py` | Cleaned blocks | Filtered blocks (noise flagged, not deleted) | **New** |
| 7 | `landmarks.py` | Filtered blocks | `Landmark` list + zone boundaries | **New** |
| 8 | `family_detector.py` | All evidence | `DocumentFamily` + confidence | **New** |
| 9 | `families/*.py` | Front-matter blocks + family priors + landmarks | Classified front-matter | **New** |
| 10 | `body_parser.py` | Body zone blocks + family hints | Classified body blocks | **New** |
| 11 | `hyphen_repair.py` | Classified blocks in order | Repaired text | **New** |
| 12 | `tree_assembler.py` | All classified blocks | `SemanticDocument` tree | **New** |
| 13 | `validator.py` | Semantic tree | Validated tree + `QualityReport` | **New** |
| 14 | `exporter.py` | Validated tree | Paperly JSON + audit log | **New** |

### Data Flow

```
ExtractionContext
    │
    ├── pages: List[PageBlocks]           ← Frozen (Stages 1–4)
    ├── document_layout: DocumentLayout   ← Frozen (Stage 4)
    ├── corpus: DocumentCorpus            ← Frozen (Corpus)
    │
    ├── ordered_blocks: List[TextBlock]   ← Frozen (Stage 4b)
    │
    ├── cleaned_blocks: List[TextBlock]   ← Stage 5 (text cleaned)
    ├── noise_flags: Dict[int, str]       ← Stage 6 (block_num → noise reason)
    │
    ├── landmarks: List[Landmark]         ← Stage 7
    │   Landmark: {type, block_num, confidence, zone_start, zone_end}
    │
    ├── family: DocumentFamily            ← Stage 8
    │   DocumentFamily: {id, confidence, signals: List[Signal]}
    │
    ├── semantic_blocks: List[SemanticBlock]  ← Stages 9–10
    │   SemanticBlock: {source_block, type, confidence, reason}
    │
    ├── semantic_tree: SemanticDocument    ← Stage 12
    │
    ├── quality_report: QualityReport     ← Stage 13
    │   QualityReport: {score, warnings, invariant_violations}
    │
    └── audit_log: List[AuditEntry]       ← Accumulated throughout
```

### Interfaces

**Family Strategy Interface:**

Every family strategy must implement:
```
classify_front_matter(
    blocks: List[TextBlock],       # Blocks in the front-matter zone (before first section heading)
    corpus: DocumentCorpus,         # Body font, title font statistics
    landmarks: List[Landmark],     # Detected structural anchors
    profile: FamilyProfile         # YAML-loaded priors
) → List[SemanticBlock]
```

**Body Parser Interface:**

The shared body parser receives:
```
classify_body(
    blocks: List[TextBlock],        # Blocks in the body zone
    corpus: DocumentCorpus,
    landmarks: List[Landmark],
    body_hints: BodyHints           # From family profile: numbering style, heading style
) → List[SemanticBlock]
```

### Failure Modes

| Failure | Detection | Recovery |
|---|---|---|
| Family detection is wrong | Parser encounters contradictory evidence (e.g., expects implicit abstract, finds explicit one) | Log warning, continue with detected family. Quality score reduced. |
| No landmarks found | Landmark list is empty | Fall back to geometric-only parsing (title = largest block, first prose = abstract). Quality score significantly reduced. |
| Front-matter parser fails | Returns zero classified blocks or all blocks are FRONT_MATTER | Fall back to `GENERIC` strategy. Log the failure. |
| Invariant violation | Validator detects (e.g., two TITLEs or zero AUTHORs) | Log violation. Do not reject the paper. Reduce quality score. Emit warning in JSON. |
| Unknown exception in any stage | Python exception | Catch at pipeline level. Log full traceback. Produce partial output up to the failing stage. Never crash silently. |

### Extension Points

1. **New family:** Create a YAML profile in `families/profiles/`. If the family's front-matter structure matches an existing strategy (e.g., it is arXiv-like), no Python code is needed — the YAML profile adjusts the priors. If the structure is truly novel, create a new strategy file in `families/`.

2. **New landmark:** Add a pattern to the landmark vocabulary in `landmarks.py`. Landmarks are pattern-matched — adding a new one is a single regex addition.

3. **New noise pattern:** Add to the noise removal stage in `noise.py`. Noise removal is independent of semantic classification.

4. **New semantic type:** Add to the `SemanticType` enum in `models.py`. Add classification logic to `body_parser.py`. Update the universal grammar. Update all invariants in `validator.py`. Update the JSON schema in `exporter.py`. **This is intentionally high-friction** — new semantic types should be rare.

5. **New validation invariant:** Add to `validator.py`. Invariants are boolean functions that take a `SemanticDocument` and return pass/fail.

### Future-Proofing

| Concern | Design Decision |
|---|---|
| New publishers | `GENERIC` strategy + YAML profiles handle most cases without code |
| Format evolution | Families are archetypes, not publisher versions. A new ACM template may create a new archetype. |
| Multi-language papers | Landmark vocabulary is extensible. Body parser is language-agnostic (typography-based). |
| Performance at scale | Every stage is stateless per-document. Pipeline is embarrassingly parallel. |
| ML integration in Phase 4+ | Each stage has clean input/output contracts. An ML-based family detector can replace the heuristic detector without changing any other stage. |

---

## Question 14: GO / NO-GO Decision

### Decision: **GO — Option B.**

**Delete the current semantic classifier. Redesign the architecture. Then reimplement.**

### Justification

**1. The current classifier has a fundamental architectural flaw — not a heuristic tuning problem.**

The single-pass sequential state machine cannot handle the diversity of document families. No amount of heuristic tuning will fix this. Every fix is a patch that introduces new failure modes.

The evidence is clear: BBR's "practice" becomes TITLE. Spanner's first abstract sentence becomes AUTHORS. USENIX's cover page creates chaos. These are not edge cases. These are **different document families** being forced through a parser designed for a single family.

**2. The frozen layers are sound.**

Stages 1–4 (ingestion, normalization, layout detection, consensus, reading order, corpus statistics) are validated and stable. The redesign does not touch them. The investment in Phase 3A.0 is preserved entirely.

**3. The new architecture has clear boundaries.**

The redesign adds 10 new modules with well-defined interfaces. Each module is independently testable. The strategy pattern isolates family-specific logic. The shared engine prevents duplication. The validation pyramid catches regressions.

**4. The cost of continuing is higher than the cost of rebuilding.**

The current classifier is 258 lines. It handles ~3 paper families poorly. Adding support for 15 more families would require ~2000+ lines of increasingly tangled heuristics, with every new rule creating cross-family regressions. The redesign will require ~1500 lines of cleaner, more modular code that handles all families.

More importantly: every day spent patching the current classifier is a day spent building on a foundation that cannot support the target scope. Technical debt accumulates daily.

**5. The risk of rebuilding is manageable.**

- The frozen layers are not affected.
- The semantic grammar (Question 5) is well-defined.
- The validation pyramid (Question 10) prevents regressions.
- The generic fallback (Question 11) ensures every paper produces output even during development.
- The corpus of 26 papers provides immediate regression coverage.

### What to Preserve

- All frozen layers (Stages 1–4, corpus statistics) — **keep.**
- The `SemanticType` enum in [models.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/models.py) — **keep and extend.**
- The `SemanticBlock` and `SemanticDocument` dataclasses — **keep and extend.**
- The invariants in [semantic_invariants.md](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/docs/phase3/semantic_invariants.md) — **keep. They are correct.**
- The audit logging pattern — **keep and formalize.**
- The confidence scoring pattern — **keep.**

### What to Delete

- [classifier.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/classifier.py) — **delete entirely.** The sequential state machine approach is the root cause of instability. Do not attempt to refactor it. Delete it and rebuild with the landmark + family + strategy architecture.
- The publisher detection in [publishers.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/publishers.py) — **replace** with the multi-signal evidence fusion detector. The current implementation is a simplistic if-else cascade that defaults to NeurIPS for unknowns — this is not acceptable.

### Execution Order

1. Build `landmarks.py` first. This is the highest-value module. Landmark detection alone will dramatically improve parsing quality even before family detection exists.
2. Build `family_detector.py` second. Evidence fusion replaces the if-else cascade.
3. Build `generic.py` (the generic fallback strategy) third. This must be excellent before any family-specific strategies are written.
4. Build `body_parser.py` fourth. The shared body parsing engine handles sections, captions, footnotes, references.
5. Build the golden dataset and regression infrastructure fifth. Before any family-specific strategy is written, the validation pipeline must be in place.
6. Build family strategies sixth, in priority order: `arxiv_like.py` → `acm_classic.py` → `acm_double.py` → `ieee_like.py` → `usenix.py` → `cvpr_like.py`.
7. Build `tree_assembler.py` and `validator.py` last. These consume the output of all previous stages.

---

> [!CAUTION]
> **Do not start writing code until this architecture document is approved.** The purpose of this review is to challenge assumptions and identify flaws before any implementation investment is made. Once the architecture is approved, it becomes the contract that all implementation must follow. Changing the architecture after implementation begins is exponentially more expensive.

---

*End of Principal Architect Review.*
