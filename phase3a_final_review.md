# Paperly — Final Principal Architecture Review & Phase 3A Roadmap

**Author:** Chief Software Architect
**Date:** 2026-07-08
**Scope:** Complete engineering review of Paperly's document understanding engine
**Purpose:** Freeze the direction. Produce the remaining roadmap. Approve or block implementation.

---

## Documents Read (Complete)

| Document | Location |
|----------|----------|
| architecture.md | Artifact |
| architecture_pressure_test.md | Artifact |
| stage1_assembly_design.md | Artifact |
| stage1_assembly_review.md | Artifact |
| stage1_assembly_freeze.md | Artifact |
| stage1_implementation_summary.md | Artifact |
| stage2_semantic_blueprint.md | Artifact |
| stage2_convergence_review.md | Artifact |
| stage2_landmark_architecture_review.md | Artifact |
| stage2_landmark_validation.md | Artifact |
| landmark_calibration_audit.md | Artifact |
| semantic_invariants.md | docs/phase3/ |
| ingest.py | extractor/ |
| normalize.py | extractor/ |
| layout.py | extractor/ |
| consensus.py | extractor/ |
| ordering.py | extractor/ |
| corpus.py | extractor/ |
| publishers.py | extractor/ |
| preprocess.py | extractor/ |
| landmarks.py | extractor/ |
| models.py | extractor/ |
| debug.py | extractor/ |
| cli.py | extractor/ |
| confidence.py | extractor/ |
| classifier.py | extractor/ (legacy, condemned) |

Every document and every source file was read in its entirety. No skimming.

---

# Part 1 — Ground Reality Review

## Phase 3A.0: Geometric Pipeline

| Attribute | Assessment |
|-----------|------------|
| **Purpose** | Extract raw text blocks, normalize coordinates, detect layout, compute reading order, identify publisher |
| **Inputs** | PDF file path |
| **Outputs** | `ExtractionContext` with `PageBlocks`, `LayoutProfile` per page, `DocumentLayout`, ordered `TextBlock` list |
| **Responsibilities** | Physical geometry only. No semantics. |
| **Non-responsibilities** | Semantic classification, text cleanup beyond ligatures, paragraph reconstruction |
| **Frozen invariants** | Coordinates normalized to [0,1]. Reading order is a pure permutation. No blocks created or destroyed. |
| **Implementation quality** | **Solid.** |
| **Validation confidence** | **High.** Validated across 12+ papers spanning ACM, IEEE, CVPR, arXiv, USENIX formats. |
| **Current maturity** | **Production-ready for its scope.** |

### Observations (Not Defects)

1. **`publishers.py` defaults to NeurIPS.** When no publisher string matches, the fallback is `NEURIPS` — a single-column assumption. This is not a bug today (the publisher profile is barely consumed downstream), but it will become dangerous when Family Detection relies on publisher priors.

2. **`corpus.py` is orphaned.** The `compute_corpus()` function exists but is never called in `cli.py` or any pipeline stage. `DocumentCorpus` is defined in `models.py` but never populated in `ExtractionContext`. This is dead infrastructure — designed but never wired.

3. **`consensus.py` mutates `TextBlock.block_type`.** Lines 68–79 of `consensus.py` set `block_type` to `NOISE` or `PARAGRAPH` based on text length. This is a mild architectural smell — the consensus stage is performing primitive semantic classification (marking blocks as NOISE based on character count) when its stated responsibility is layout consensus. It does not cause harm today, but it is a responsibility leak.

4. **`classifier.py` still exists.** The architecture explicitly condemned this file ("delete entirely"). It remains in the repository. It is not called by any pipeline stage, but its presence is confusing for anyone reading the codebase.

### Verdict: Phase 3A.0

> **Accurate.** The geometric pipeline is complete and production-ready. The statement that it is "frozen" is correct. The three minor observations above are not blocking issues.

---

## Phase 3A.1: Typographic Assembly

| Attribute | Assessment |
|-----------|------------|
| **Purpose** | Reconstruct coherent reading units from fragmented PyMuPDF blocks |
| **Inputs** | Ordered `TextBlock` list from Phase 3A.0 |
| **Outputs** | `List[TypographicGroup]` stored in `ExtractionContext.assembled_groups` |
| **Responsibilities** | Geometric merging based on vertical proximity, font continuity, horizontal alignment, hyphenation |
| **Non-responsibilities** | Semantic classification, cross-page merging, cross-column merging |
| **Frozen invariants** | Every raw block appears in exactly one group. Provenance preserved via `source_blocks`. No semantic guessing. Conservative policy = false negatives over false positives. |
| **Implementation quality** | **Strong.** |
| **Validation confidence** | **High.** Validated with `StageQualityReport` across 7+ papers. Average confidence 0.90. |
| **Current maturity** | **Frozen and stable.** |

### Critical Observation

The pressure test (architecture_pressure_test.md §2A, §2B) argued that "block merging" — specifically paragraph reconstruction — was the "most critical missing stage." The convergence review (stage2_convergence_review.md §6) declared this "already solved" by Stage 3A.1.

**My independent assessment:** The convergence review is *partially* correct. Stage 3A.1 merges *adjacent* blocks with matching typography into groups. This handles the common case of multi-line paragraphs split into per-line blocks. But it does NOT handle:

- **Run-in section headers** merged with body text (e.g., ReAct's `1 INTRODUCTION A unique feature of...`). Stage 3A.1 correctly assembles these because the font is uniform — but the result is a single `TypographicGroup` containing both the heading and the paragraph. Landmark detection then fails because the group is too long (>150 chars) to match the section regex.
- **Fragmented inline formatting** where a heading like "**1.** Introduction" is split into two blocks with different bold flags. Stage 3A.1 may refuse to merge these because the bold flag differs. Neither fragment matches the section pattern alone.

These are not Stage 3A.1 bugs. They are architectural boundary cases that downstream stages must handle. The convergence review was correct to freeze Stage 3A.1, but incorrect to claim paragraph reconstruction is "solved." It is *partially* solved for the dominant case.

### Verdict: Phase 3A.1

> **Architecturally complete.** The implementation is frozen and stable. The residual weaknesses (run-in headers, fragmented formatting) are correctly classified as Stage 3A.2+ responsibilities, not Stage 3A.1 defects.

---

## Phase 3A.2: Landmark Detection

| Attribute | Assessment |
|-----------|------------|
| **Purpose** | Discover high-confidence structural landmarks that partition the document into zones |
| **Inputs** | `List[TypographicGroup]` from Stage 3A.1 |
| **Outputs** | `LandmarkReport` containing `StructuralFence` and `DocumentAnchor` lists |
| **Responsibilities** | Detect explicit structural signals (headings, title, emails, keywords) |
| **Non-responsibilities** | Implicit region detection, semantic classification, family detection |
| **Frozen invariants** | Never mutate groups. Reference by `group_ids`. No semantic leakage. No family dependency. Deterministic. Explainable via evidence ledgers. |
| **Implementation quality** | **Partially complete.** Core structure is sound; heuristics need calibration. |
| **Validation confidence** | **Medium.** The validation exposed severe false negatives on section headings. |
| **Current maturity** | **Architecture frozen. Heuristics not frozen.** |

### Architecture vs Implementation Gap Analysis

| Issue | Category | Evidence |
|-------|----------|----------|
| `SECTION_PAT` regex rejects headers with digits/punctuation | **Heuristic calibration** | SQLite `2.2.2 Write-ahead log mode.` rejected; MapReduce `4. Map-Reduce` rejected |
| Run-in headers merged with body text cause length rejection | **Upstream boundary case** (Stage 3A.1) | ReAct `1 INTRODUCTION A unique feature of...` is one group, fails len < 150 |
| Multiple TITLE_CANDIDATE anchors for single title | **Heuristic calibration** | MapReduce produces 2 title anchors |
| EMAIL over-detection on bracketed author lists | **Upstream assembly** (Stage 3A.1) | SQLite `{a, b, c}@domain.com` fragments into 7 anchors |
| Unnumbered bold relies on `istitle()` | **Heuristic calibration** | Sentence-case headers missed; false positives on figure captions avoided |
| `FenceType` enum uses `SECTION_HEADING` instead of `FIRST_SECTION_HEADING` | **Architecture deviation** | The landmark architecture review specified `FIRST_SECTION_HEADING`. Implementation emits `SECTION_HEADING` for ALL numbered sections. |

### The `FIRST_SECTION_HEADING` Problem

> [!IMPORTANT]
> The architecture review ([stage2_landmark_architecture_review.md](file:///C:/Users/mayur/.gemini/antigravity-ide/brain/5912665f-d0cb-421b-a36b-93c88d699f7d/stage2_landmark_architecture_review.md) Topic 1) specified that `StructuralFence` should have `FIRST_SECTION_HEADING` — a fence that marks the boundary between front-matter and body. The implementation instead emits `SECTION_HEADING` for *every* numbered section.

This is not necessarily wrong — emitting all section fences provides more data for downstream Zonal Partitioning. But it conflates two different architectural roles:

1. **Topological fence** (partitions the document into zones) — only the *first* section heading serves this role.
2. **Structural annotation** (marks every section boundary) — all section headings serve this role.

The current `FenceType.SECTION_HEADING` is used for both purposes. Downstream code will need to determine which `SECTION_HEADING` fence is the *first* one to perform zonal partitioning. This is trivial (sort by `reading_order_start`, take the first), but it should be documented.

**Category:** Minor architecture deviation. Not blocking.

### Verdict: Phase 3A.2

> **Architecture is sound. Implementation is incomplete.** The `StructuralFence` / `DocumentAnchor` split is correct. The evidence-based confidence model is correct. The frozen invariants are respected. But the section heading regex is catastrophically miscalibrated, causing ~80% miss rate on non-standard papers. This is a **heuristic calibration** problem, not an architectural problem.

---

# Part 2 — Architecture vs Implementation Classification

| Weakness | Category | Evidence | Required Action |
|----------|----------|----------|-----------------|
| Section regex too strict | Heuristic calibration | `SECTION_PAT` suffix `([A-Z][A-Za-z\s]+)$` rejects punctuation/digits | Relax regex. Keep bold+length as primary evidence. |
| Run-in headers | Upstream boundary case | ReAct's `1 INTRODUCTION A unique...` is one group | Landmark detection should attempt prefix-matching on long groups, not only full-string matching. |
| Title fragmentation | Heuristic calibration | MapReduce produces 2 title anchors | Merge contiguous max-font-size groups into one anchor. |
| Email over-detection | Upstream assembly | Bracketed email lists fragment | Not a landmark problem. Email anchor is correct per-group. |
| `corpus.py` never called | Implementation gap | Dead code | Wire into pipeline or remove. |
| `classifier.py` still exists | Implementation hygiene | Condemned file remains | Delete. |
| `publishers.py` defaults to NeurIPS | Implementation risk | Arbitrary fallback | Change default to a generic `UNKNOWN` publisher or handle explicitly. |
| `consensus.py` marks block_type | Responsibility leak | Lines 68–79 set NOISE/PARAGRAPH | Document as known debt. Not blocking. |

---

# Part 3 — Phase 3A.2 Architecture Review

### Is Landmark Detection architecturally complete?

**Yes, for its current scope.** The Fence/Anchor distinction is the correct abstraction. The evidence ledger provides explainability. The frozen invariants prevent semantic leakage.

### Are responsibilities correctly separated?

**Yes.** Landmark Detection finds explicit signals. It does not guess implicit regions. It does not classify body text. It does not depend on family detection. These boundaries are clean.

### Is another architectural layer still missing?

**Yes. Observability is missing.** There is no structured way to ask "why was group X rejected by heuristic Y?" The audit log in `ExtractionContext` records stage-level events, but does not record per-group per-heuristic evaluation traces. This makes calibration work expensive — the calibration audit had to write a custom external script to replicate the internal decision logic.

### Are we prematurely implementing before understanding?

**No.** The architecture has been reviewed three times (blueprint, convergence, final review). The implementation contract is clear. The remaining work is heuristic calibration and downstream stage implementation, not architectural discovery.

### Would I change anything before implementation continues?

**One thing:** Before building any downstream stages, calibrate the section heading regex. The current ~80% miss rate on section headings means Zonal Partitioning will receive garbage inputs for half the corpus. Calibrating one regex is 15 minutes of work with massive downstream impact.

---

# Part 4 — Long-Term Scalability (100,000+ Papers)

### What naturally scales

1. **Frozen geometric layers.** PDF geometry does not change. `ingest.py`, `normalize.py`, `layout.py`, `ordering.py` will work on papers from any decade or publisher without modification.

2. **The Fence/Anchor vocabulary.** Adding new landmark types (e.g., `METHODOLOGY_HEADING`) requires adding a regex to a vocabulary dictionary and an enum value. O(1) cost per addition.

3. **The evidence-based confidence model.** Every detection carries a numeric score and categorical strength. This enables automated quality triage at scale.

4. **Conservative assembly policy.** False negatives (fragmented groups) are recoverable downstream. False positives (incorrectly merged groups) are not. The conservative default is the correct scalability choice.

### What becomes technical debt

1. **`publishers.py` as an if-else cascade.** At 100 publishers, this becomes unmaintainable. Needs migration to data-driven detection (the architecture calls this "Family Detection" but it has not been implemented).

2. **Hardcoded thresholds scattered across files.** `confidence.py` has some thresholds. `preprocess.py` has `0.85` hardcoded at line 72 and again at line 202. `landmarks.py` has `150` (max section length) and `0.5` (font size tolerance) embedded inline. At 100K papers, these thresholds will need corpus-driven calibration, and they are not centralized.

3. **The `ExtractionContext` god object.** Every stage reads and writes the same mutable object. At scale with concurrent processing, this becomes a synchronization hazard. For a single-developer project, it is pragmatically correct. For a team, it needs stage-specific input/output types.

4. **Lack of regression infrastructure.** There are no regression snapshots, no golden datasets, no automated validation suites. At 100K papers, every heuristic change risks silent regressions on thousands of previously-correct papers.

### What will fail

1. **The `GENERIC` fallback.** The architecture promises that unknown publishers are handled by a generic landmark-only parser. This parser does not exist. When it does exist, the calibration audit shows that even the landmark detector misses ~80% of sections on non-standard papers. A generic parser receiving incomplete landmarks will produce poor results.

2. **Font fingerprinting.** The architecture proposes font fingerprints as a family detection signal. But `ingest.py` extracts the *dominant* font per block, losing intra-block font transitions. A heading rendered as "**1.** Introduction" where "1." is bold and "Introduction" is regular will have its dominant font determined by character count — the regular font wins. Font fingerprinting at scale will require span-level font preservation, not block-level dominant font.

---

# Part 5 — Observability (From First Principles)

### Should a production-grade document understanding engine contain an observability layer?

**Unconditionally yes.**

A deterministic heuristic engine is only as good as its maintainer's ability to understand its decisions. If a heuristic fires incorrectly on 500 papers, the maintainer must be able to answer: "What evidence caused the firing? What evidence was missing? What threshold was exceeded?" Without observability, every debugging session requires reading source code and mentally simulating the execution path.

### What it should do

1. **Record per-group evaluation traces.** For every `TypographicGroup`, record which heuristics were considered, what evidence was present/absent, what score was computed, and whether the group was accepted or rejected.

2. **Record rejection reasons.** Every rejected candidate must have a human-readable reason string explaining *why* it was rejected. Not "failed threshold" — instead: "Regex matched numbering '3.2' but text 'IPv6 Implementation' contains digits, failing alphabetical constraint."

3. **Provide corpus-level aggregation.** After processing N papers, produce statistics: which heuristic has the highest false-negative rate? Which rejection reason is most common? Which papers have the lowest confidence?

4. **Be accessible via CLI.** A developer should be able to run `python -m extractor inspect <pdf>` and see every decision for every group.

5. **Support JSON export.** The complete evaluation trace should be exportable as structured JSON for programmatic analysis.

### What it should NEVER do

1. **Never influence parsing.** The observability layer is strictly read-only. It records decisions; it does not make them. It must not alter thresholds, weights, or evidence based on what it observes.

2. **Never block the pipeline.** If observability fails (e.g., a formatting error in a reason string), the parsing pipeline must continue unaffected.

3. **Never store mutable text.** Like everything else in Paperly, the observability layer must reference groups by ID, not by copied text.

### Should it remain completely read-only?

**Yes.** The observability layer is a lens, not a lever. It explains; it does not control.

---

# Part 6 — Engineering Roadmap (Remainder of Phase 3A)

## Milestone 1: Landmark Calibration

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Fix the section heading regex and title merging to bring section detection from ~30% to ~90% on the benchmark corpus |
| **Why this stage exists** | Downstream stages (Zonal Partitioning, Front-Matter Parsing, Body Parsing) depend on accurate landmarks. Feeding them garbage landmarks produces garbage zones. |
| **Inputs** | Current `landmarks.py` with frozen architecture |
| **Outputs** | Calibrated `landmarks.py` with relaxed `SECTION_PAT`, title merging logic, and potentially a run-in header prefix-match |
| **Responsibilities** | Calibrate heuristic thresholds. Do NOT add new heuristic categories. Do NOT change the data model. |
| **Non-responsibilities** | Architectural changes, implicit region detection, family detection |
| **Required abstractions** | None new. Use existing `StructuralFence`, `DocumentAnchor`, `LandmarkEvidence`. |
| **Required data models** | None new. |
| **Frozen invariants** | All 8 invariants from the landmark architecture review remain. |
| **Expected failure modes** | Relaxing the regex too far may introduce false positives on numbered list items (e.g., "1. This paper proposes..."). The length and typography constraints must compensate. |
| **Validation methodology** | Re-run the 12-paper benchmark. Compare fence counts before/after. Target: ≥80% section heading recall across the corpus. |
| **Manual inspection** | Generate debug PDFs for Spanner, MapReduce, Cassandra, SQLite, ReAct. Visually confirm that previously-missed sections are now detected. |
| **Benchmark requirements** | Section heading recall ≥ 80%. False positive rate < 5%. |
| **Exit criteria** | The calibration audit's 5 root causes are addressed. The validation report shows ≥80% section recall. No new false positives introduced. |

---

## Milestone 2: Engineering Observability Layer

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Build the inspection infrastructure that makes every heuristic decision traceable |
| **Why this stage exists** | Without observability, every future calibration cycle requires writing throwaway audit scripts. Observability is reusable infrastructure that pays dividends indefinitely. |
| **Inputs** | `ExtractionContext` with `assembled_groups` and `landmark_report` |
| **Outputs** | `InspectionReport` containing per-group evaluation traces, rejection reasons, confidence breakdowns, and corpus summary statistics |
| **Responsibilities** | Recording decisions. Formatting human-readable reports. JSON export. |
| **Non-responsibilities** | Making decisions. Altering parsing logic. Tuning thresholds. |
| **Required abstractions** | `GroupInspectionRecord` (per-group trace), `HeuristicEvaluation` (per-heuristic result), `InspectionReport` (corpus summary) |
| **Required data models** | New models in `inspector.py` or `models.py`. These are observability-only; they do not affect parsing. |
| **Frozen invariants** | Observability never mutates groups. Observability never influences parsing. Observability is optional — the pipeline works identically without it. |
| **Expected failure modes** | Performance overhead if traces are excessively verbose. Mitigate: make trace depth configurable. |
| **Validation methodology** | Run `inspect` command on 7 benchmark papers. Verify every rejection has a human-readable reason. Verify confidence math is traceable. |
| **Manual inspection** | Read the output for Spanner. Confirm you can trace exactly why each section header was rejected. |
| **Benchmark requirements** | 100% of rejected candidates must have a non-empty reason string. |
| **Exit criteria** | Every heuristic decision is explainable via the CLI. JSON export works. No parsing behavior changed. |

---

## Milestone 3: Zonal Partitioning

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Use calibrated landmarks to partition the document into topological zones: Front-Matter, Body, References, Appendix |
| **Why this stage exists** | Zonal Partitioning is the single most valuable architectural operation. It constrains all downstream classifiers to operate within their zone, preventing cascading errors (e.g., a body paragraph being classified as an author). |
| **Inputs** | `LandmarkReport` (calibrated), `List[TypographicGroup]` |
| **Outputs** | `ZonalPartition` containing `front_matter_groups`, `body_groups`, `references_groups`, `appendix_groups` |
| **Responsibilities** | Slicing the group list at fence boundaries. Handling missing fences gracefully. |
| **Non-responsibilities** | Classifying content within zones. Detecting implicit regions. |
| **Required abstractions** | `ZonalPartition` dataclass. Zone boundary resolution logic. |
| **Required data models** | `ZonalPartition` with `List[TypographicGroup]` per zone. Add to `ExtractionContext`. |
| **Frozen invariants** | Every group appears in exactly one zone. No groups are created or destroyed. Zone boundaries are fence-aligned. |
| **Expected failure modes** | Papers with no detected fences produce a single undifferentiated zone. Papers with multiple `REFERENCES_HEADING` fences (e.g., supplementary material) need first-match disambiguation. |
| **Validation methodology** | For each benchmark paper, verify that the front-matter zone contains only pre-body content and the body zone contains only sections. |
| **Manual inspection** | Debug PDF overlays colored by zone (e.g., green = front-matter, blue = body, orange = references). |
| **Benchmark requirements** | Zone boundaries correct on ≥90% of benchmark papers. |
| **Exit criteria** | Zones are correctly partitioned for papers with explicit landmarks. Graceful degradation for papers without. |

---

## Milestone 4: Front-Matter Parsing (Generic Strategy)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Classify groups within the front-matter zone into TITLE, AUTHORS, AFFILIATIONS, ABSTRACT, KEYWORDS, FRONT_MATTER |
| **Why this stage exists** | Front-matter is the most publisher-variable region. It requires family-guided classification. The generic strategy handles papers without family-specific support. |
| **Inputs** | `front_matter_groups` from `ZonalPartition`, `DocumentCorpus` (body font stats), `LandmarkReport` (title anchor, keywords anchor, abstract fence) |
| **Outputs** | Classified `SemanticBlock` list for front-matter groups |
| **Responsibilities** | Title detection (via anchor), author detection (positional + typographic), abstract detection (via fence or positional heuristic), keyword detection (via anchor) |
| **Non-responsibilities** | Body parsing. Section detection. Figure/table detection. |
| **Required abstractions** | `FrontMatterStrategy` interface. `GenericFrontMatterStrategy` implementation. |
| **Required data models** | `SemanticBlock` (already exists in models.py) |
| **Frozen invariants** | Never mutate `TypographicGroup`. Every group in the front-matter zone receives exactly one classification. FRONT_MATTER is the catch-all for unclassifiable preamble content. |
| **Expected failure modes** | Implicit abstracts (no "Abstract" fence) on ACM papers. Multi-page author lists. Author blocks with unusual formatting. |
| **Validation methodology** | For each benchmark paper, compare detected TITLE and ABSTRACT against human expectations. |
| **Manual inspection** | Debug PDF with front-matter classifications overlaid. |
| **Benchmark requirements** | TITLE correct on 100% of papers. ABSTRACT correct on ≥80% of papers (allowing miss on implicit-abstract papers). |
| **Exit criteria** | Generic strategy handles all papers with explicit landmarks. Quality degrades gracefully on implicit-abstract papers. |

---

## Milestone 5: Body Parsing (Shared Engine)

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Classify groups within the body zone into SECTION_HEADING, PARAGRAPH, FIGURE_CAPTION, TABLE_CAPTION, EQUATION, FOOTNOTE, LIST_ITEM |
| **Why this stage exists** | The body zone is the largest and most uniform region. A shared engine with configurable hints handles it across all publisher families. |
| **Inputs** | `body_groups` from `ZonalPartition`, section fences from `LandmarkReport`, family-provided body hints (section numbering style, heading typography) |
| **Outputs** | Classified `SemanticBlock` list for body groups |
| **Responsibilities** | Section hierarchy detection. Caption detection (regex: `Figure N:`, `Table N:`). Paragraph classification (default). |
| **Non-responsibilities** | Front-matter parsing. Figure/table image extraction (Phase 3B). Reference item parsing. |
| **Required abstractions** | `BodyHints` (section numbering style, heading style). Caption detection regex vocabulary. |
| **Required data models** | `SemanticBlock` with `section_id` populated. |
| **Frozen invariants** | Every body group receives exactly one classification. PARAGRAPH is the default fallback. Section hierarchy is derived from numbering depth (e.g., "3.2" = subsection of "3"). |
| **Expected failure modes** | Equations misclassified as PARAGRAPH (mathematical text without clear equation formatting). List items misclassified as PARAGRAPH (bullets lost in PDF extraction). |
| **Validation methodology** | Section heading detection recall ≥ 90%. Caption detection precision ≥ 95%. |
| **Manual inspection** | Debug PDF with body classifications overlaid. |
| **Benchmark requirements** | Section headings match landmark fences. Captions correctly identified. |
| **Exit criteria** | Body parsing produces correct section hierarchy for papers with numbered sections. Unnumbered section support is functional but may have lower recall. |

---

## Milestone 6: Tree Assembly & Validation

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Assemble classified `SemanticBlock` lists into a hierarchical `SemanticDocument` tree and validate structural invariants |
| **Why this stage exists** | The semantic tree is the interface boundary between extraction and presentation. Everything downstream (rendering, search, export) consumes only the tree. |
| **Inputs** | Classified `SemanticBlock` lists from Milestones 4–5, `references_groups` and `appendix_groups` from `ZonalPartition` |
| **Outputs** | `SemanticDocument` tree + `QualityReport` |
| **Responsibilities** | Nesting sections/subsections. Attaching blocks to sections. Computing quality score. Checking hard and soft invariants. |
| **Non-responsibilities** | Classification (already done). Heuristic tuning. |
| **Required abstractions** | `QualityReport` with hard/soft invariant tracking. |
| **Required data models** | `SemanticDocument` (already exists), `QualityReport` (new). |
| **Frozen invariants** | HARD: No blocks unclassified. No blocks lost. SOFT: Exactly 1 TITLE. TITLE before ABSTRACT. ABSTRACT before first SECTION. |
| **Expected failure modes** | Papers with unusual structure may violate soft invariants. The quality report must reflect this without crashing. |
| **Validation methodology** | All hard invariants pass on 100% of papers. Soft invariant violations produce warnings, not failures. |
| **Exit criteria** | `SemanticDocument` is produced for every benchmark paper. Quality scores reflect actual parse quality. |

---

## Milestone 7: Regression Infrastructure & Golden Dataset

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Build the automated safety net that prevents "fix one paper, break another" |
| **Why this stage exists** | Every heuristic change risks regressions on previously-correct papers. Without regression snapshots, regressions are invisible until a user reports them. |
| **Inputs** | The full benchmark corpus |
| **Outputs** | Per-paper regression snapshots (JSON). 5 golden papers with human-verified block labels. |
| **Responsibilities** | Snapshot generation. Snapshot comparison. Diff reporting. |
| **Exit criteria** | Every benchmark paper has a snapshot. 5 golden papers have human-verified labels. `python -m extractor test` re-runs all papers and reports diffs. |

---

## Implementation Order

```
Milestone 1: Landmark Calibration          [~2 hours]
    ↓
Milestone 2: Engineering Observability     [~4 hours]
    ↓
Milestone 3: Zonal Partitioning           [~3 hours]
    ↓
Milestone 4: Front-Matter Parsing         [~6 hours]
    ↓
Milestone 5: Body Parsing                 [~6 hours]
    ↓
Milestone 6: Tree Assembly & Validation   [~4 hours]
    ↓
Milestone 7: Regression Infrastructure    [~3 hours]
```

> [!IMPORTANT]
> Milestones 1 and 2 must be completed before Milestone 3. Zonal Partitioning depends on calibrated landmarks, and the observability layer must exist before additional heuristic stages are built — otherwise debugging those stages will require ad-hoc scripting.

---

# Final Engineering Verdict

## Classification: **B. Architecture Complete — Implementation Incomplete**

### Evidence

1. **The architectural decisions are sound.** The Geometry → Structure → Semantics pipeline, the Fence/Anchor distinction, the zone-constrained classification model, the evidence-based confidence system, the immutable-groups invariant, the conservative assembly policy — these are all correct and well-justified across three independent reviews.

2. **The implementation is incomplete.** Only two of the seven planned stages have been implemented (Typographic Assembly and Landmark Detection). The semantic engine (zonal partitioning, front-matter parsing, body parsing, tree assembly, validation) does not yet exist.

3. **The existing implementation is architecturally compliant.** The landmarks implementation obeys every frozen invariant. Its weakness is heuristic calibration, not architectural violation.

4. **No further architectural design is needed.** The remaining milestones are implementation tasks with clear inputs, outputs, and contracts. The architecture is frozen and ready for execution.

---

# Recommendations

### 1. Would I approve continuing implementation today?

**YES.**

The architecture has survived three independent pressure tests. The frozen geometric layers are stable. The landmark detection architecture is correct (the regex calibration is a 15-minute fix, not an architectural revision). The remaining milestones have clear specifications.

### 2. What should be implemented next?

**Milestone 1 (Landmark Calibration)** — immediately. Then **Milestone 2 (Observability)** — before any downstream semantic stages.

### 3. What should the engineering team absolutely avoid doing?

- **Do NOT build family-specific strategies yet.** Build the generic strategy first. Make it excellent. Add family-specific overrides only when the generic strategy demonstrably fails on specific publisher archetypes.
- **Do NOT introduce YAML profiles.** The pressure test correctly identified this as premature abstraction. Hardcode priors in Python until 100+ papers demand otherwise.
- **Do NOT build a `families/` directory.** Start with a single `families.py`. Split when it exceeds 400 lines.
- **Do NOT skip the regression infrastructure.** Milestone 7 is not optional. Without it, every future heuristic change is a gamble.

### 4. Three biggest risks that could silently damage Paperly

1. **Calibrating heuristics without observability.** If you tune the section regex without seeing per-group evaluation traces, you are guessing. Build observability first, then calibrate.

2. **Scope creep into ML.** The architecture is deterministic by design. The temptation to "just add a small model for X" will arise. Resist it. Every ML component introduces non-determinism, opaque failures, and dependency complexity.

3. **Ignoring the `GENERIC` fallback.** The generic strategy handles unknown publishers. If it is neglected in favor of family-specific strategies, the system becomes brittle for any paper outside the known corpus.

### 5. If I became the permanent architect today

**Protect at all costs:**
- The Geometry → Structure → Semantics pipeline ordering
- The immutability of `TypographicGroup`
- The evidence-based confidence model
- The Fence/Anchor distinction

**Simplify:**
- Delete `classifier.py` 
- Wire `corpus.py` into the pipeline or delete it
- Centralize all thresholds in `confidence.py`
- Replace the publisher fallback in `publishers.py` from NeurIPS to an explicit UNKNOWN profile

**Postpone:**
- YAML family profiles (until 100+ papers)
- `families/` directory structure (until the file exceeds 400 lines)
- Multi-language landmark vocabulary (until non-English papers enter the corpus)
- Figure/table extraction (Phase 3B)

---

> [!CAUTION]
> **Do not begin Milestone 3 or later until Milestones 1 and 2 are complete and validated.** Zonal Partitioning on uncalibrated landmarks is architectural malpractice.

---

*End of Final Principal Architecture Review.*
