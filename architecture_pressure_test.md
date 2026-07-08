# Paperly Architecture — Pressure Test

## Adversarial Review of the Proposed Semantic Reconstruction Architecture

> **Reviewer:** Second Principal Engineer
> **Date:** 2026-07-06
> **Posture:** Assume the original architect is wrong. Find every flaw.
> **Ground Rule:** No implementation. No code. Architecture only.

---

## 1. What Is Overengineered?

### 1A. The YAML Family Profiles Are Premature Abstraction

The architecture proposes a `families/profiles/` directory with YAML files that declaratively define family priors:

```yaml
family_id: MDPI_SINGLE
priors:
  title_size_ratio: 1.1
  abstract_style: explicit
  section_numbering: arabic
  heading_style: bold_numbered
```

This is elegant in theory. In practice, it is premature.

**The problem:** You have 26 papers. You have studied 7 layout families in detail. You do not yet know which priors actually matter. You are designing a declarative configuration system for a problem you have not yet solved.

YAML profiles make sense when:
- You have parsed 500+ papers
- You know exactly which 8–12 parameters actually vary between families
- The generic parser is mature and its behavior is well-understood
- Adding a new family is a frequent operation (monthly+)

None of these are true today. Today you need to write the generic parser, discover what fails, discover what priors actually disambiguate, and only then formalize them into a profile schema.

**Recommendation:** Start with hardcoded priors inside each strategy file. After 3–4 strategy files exist and you see the common pattern, extract the YAML profile system. Premature configuration is worse than no configuration — it forces you to design an interface before you understand the problem.

### 1B. The `families/` Subdirectory Is Too Deep Too Early

The proposed structure:

```
families/
├── registry.py
├── base_strategy.py
├── generic.py
├── arxiv_like.py
├── acm_classic.py
├── acm_double.py
├── ieee_like.py
├── usenix.py
├── cvpr_like.py
└── profiles/
    ├── arxiv_single.yaml
    ├── neurips_single.yaml
    └── ...
```

This is 10+ files in a subdirectory for a feature that does not exist yet. You are creating organizational structure for code that has not been written. This is the hallmark of an architect who designs directories instead of solving problems.

**The real risk:** A developer opening this codebase for the first time sees 10 files in `families/` and thinks the family system is a major, complex subsystem. In reality, each strategy file will be 50–100 lines. The registry will be 20 lines. The base class will be 15 lines. The entire family system is ~500 lines — it does not need its own subdirectory, a base class, and a registry pattern at day one.

**Recommendation:** Start with `families.py` — one file containing the generic strategy and the base interface. When you have 3+ strategies and the file exceeds 300 lines, split into a directory. Let the code demand the structure instead of pre-building the structure.

### 1C. Fourteen Stages Is Excessive

The proposed pipeline has 14 stages:

| # | Stage |
|---|---|
| 1 | Ingestion |
| 2 | Block Extraction + Normalization |
| 3 | Layout Analysis |
| 4 | Layout Consensus |
| 4b | Reading Order |
| C | Corpus Statistics |
| 5 | Text Cleanup |
| 6 | Noise Removal |
| 7 | Landmark Detection |
| 8 | Family Detection |
| 9 | Front-Matter Parsing |
| 10 | Body Parsing |
| 11 | Hyphen Repair |
| 12 | Tree Assembly |
| 13 | Validation |
| 14 | JSON Export |

Six of those stages are frozen. The architecture proposes adding **ten** new stages to a pipeline that currently has six. Each stage has an input, an output, an interface contract, and a module. Each module must be debugged independently, tested independently, and its failure modes catalogued.

**Question:** Does every stage truly need to be a separate module?

- **Stage 5 (Cleanup) and Stage 6 (Noise Removal)** operate on the same data (TextBlock list), are both pre-processing steps, and have no dependencies between them. They could be one stage: "Pre-processing."

- **Stage 7 (Landmarks) and Stage 8 (Family Detection)** are conceptually linked. Landmarks inform family detection (the presence of "Abstract" as an explicit heading is a family signal). Family detection uses landmarks. Separating them forces landmarks to be detected without knowing the family, and forces family detection to be finalized without knowing whether the family-specific landmark vocabulary would change anything. These should be one stage: "Document Identification."

- **Stage 12 (Tree Assembly), Stage 13 (Validation), and Stage 14 (Export)** are sequential, never run independently, and the output of one is always the input to the next. No user of this pipeline will ever want to run tree assembly without validation, or validation without export. These could be one stage: "Finalization."

**This reduces 14 stages to 10.** Still modular. Less overhead.

| # | Stage | Status |
|---|---|---|
| 1–4b, C | Frozen layers | Frozen |
| 5 | Pre-processing (cleanup + noise) | New |
| 6 | Document Identification (landmarks + family) | New |
| 7 | Front-Matter Parsing | New |
| 8 | Body Parsing | New |
| 9 | Text Repair (hyphens + paragraph merging) | New |
| 10 | Finalization (tree assembly + validation + export) | New |

Each merged stage is internally organized into clear substeps. The substeps share a module file, not a separate module. This reduces file count without reducing modularity.

### 1D. The Evidence Fusion Detector Is Overdesigned for the Current Scale

The architecture proposes a "multi-signal evidence fusion" system with three tiers of signals, weighted confidence aggregation, and per-signal logging.

For 26 papers across 7 families, this is a weighted voting system for an election with 7 candidates and 26 voters. The overhead of designing, tuning, and debugging the fusion weights exceeds the cost of a simple priority-ordered detector.

**The honest truth:** Publisher string matching (Tier 1 signals) alone correctly identifies the family for 22 of your 26 papers. The remaining 4 (TCP Congestion, End-to-End Arguments, UNIX, Hyperloop) are unusual papers that may not even belong in your initial scope.

**Recommendation:** Implement the detector as a simple priority cascade:
1. Try publisher strings first. If match → done.
2. Try copyright/license blocks. If match → done.
3. Try font fingerprint + column layout combination. If match → done.
4. If nothing matches → GENERIC.

This is not the beautiful multi-signal fusion system. It is the system you need today. Upgrade to weighted fusion when you have 200+ papers and the priority cascade demonstrably fails.

---

## 2. What Is Underengineered?

### 2A. There Is No Paragraph Merging Strategy

The architecture discusses "hyphen repair" and "block merging" but provides no architectural treatment of **paragraph reconstruction.** This is a critical gap.

PDF text blocks from PyMuPDF do not correspond to paragraphs. A single paragraph may be split across 2–5 text blocks depending on how LaTeX rendered the page. Two consecutive blocks that are part of the same paragraph may have:
- Identical x0 values (continuation)
- Identical font and size
- No gap larger than ~1.5× the line height

Merging these blocks into paragraphs is not text cleanup. It is not semantic classification. It is a **structural reconstruction operation** that must happen after reading order is established but before semantic classification begins. If you classify un-merged blocks, you might classify the second half of a title as AUTHORS because it follows the first half of the title.

The original architecture spec ([phase_3_document_understanding_architecture.md](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/docs/phase3/phase_3_document_understanding_architecture.md) lines 541–544) mentions paragraph reconstruction in Stage 8 (Content Assembly), but the proposed redesign moves it to Stage 11 (Hyphen Repair). This is too late. By Stage 11, you have already classified the un-merged blocks, potentially incorrectly.

**The correct placement:** Paragraph merging belongs between noise removal and landmark detection. Merge adjacent blocks that share font, size, and approximate x0 into unified TextBlocks. Then detect landmarks on the merged blocks. Then classify the merged blocks.

**This is the most important missing stage in the architecture.**

### 2B. There Is No Treatment of Block Fragmentation

Related to 2A: PyMuPDF sometimes splits what is visually a single text block into multiple blocks based on font changes within a line. A section heading like "**1.** Introduction" where the number is bold and the word is regular may be extracted as two blocks:
- Block A: "1." (bold, 10pt)
- Block B: "Introduction" (regular, 10pt)

The landmark detector would miss this because neither block by itself matches "1. Introduction." The section heading detector would miss it because neither block starts with a number followed by text.

The architecture assumes that TextBlocks from PyMuPDF are semantically coherent units. They are not. They are typographic runs. A pre-processing merge step must reconstruct coherent blocks from fragmented spans before any semantic analysis.

### 2C. The ExtractionContext Is Becoming a God Object

The proposed `ExtractionContext` accumulates all state:

```
ExtractionContext
├── pages
├── document_layout
├── corpus
├── ordered_blocks
├── cleaned_blocks
├── noise_flags
├── landmarks
├── family
├── semantic_blocks
├── semantic_tree
├── quality_report
└── audit_log
```

This object grows at every stage. By Stage 14, it contains the entire history of the pipeline: raw blocks, cleaned blocks, noise flags, landmarks, family, semantic blocks, the tree, the quality report, and the full audit log. Every stage has access to everything.

This is convenient but dangerous:
- **Stage 10 (Body Parsing) can read raw blocks from Stage 2.** Should it? No. It should only see cleaned, noise-filtered, ordered blocks. But the object does not enforce this.
- **Testing becomes coupled.** To test Stage 8 (Family Detection), you must construct a full ExtractionContext with pages, blocks, layout, and corpus. This is test fixture bloat.
- **Debugging is non-local.** When a bug occurs in Stage 10, you must inspect the entire ExtractionContext to determine whether the problem is in Stage 10 or was inherited from Stages 5–9.

**Recommendation:** Do not try to fix this now. It is the right pragmatic choice for a solo-developer project. But document it as a known architectural debt. If the team grows to 3+ developers, introduce stage-specific input types that restrict what each stage can see.

### 2D. Figure and Table Extraction Is Unaddressed

The architecture is a semantic reconstruction engine, but it says nothing about how figures and tables will be handled in the new pipeline. The original architecture ([phase_3_document_understanding_architecture.md](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/docs/phase3/phase_3_document_understanding_architecture.md), Stage 7) had detailed figure extraction, vector detection, and table rasterization plans. The new architecture mentions FIGURE_REF and TABLE_REF in the semantic grammar but does not describe when or how figure/table regions are detected, extracted, and matched to captions.

This is presumably deferred to Phase 3B, but the architecture should at least specify **where** figure/table extraction fits in the pipeline and **what interface** it uses. If figure extraction happens after semantic classification, it needs the semantic tree. If it happens before, it needs the layout profile. This dependency must be documented.

---

## 3. Can the Architecture Parse Papers from Publishers We Have Never Seen?

### Honest Assessment: Partially.

The architecture claims that the GENERIC parser with landmark detection handles unknown publishers at 80%+ accuracy. I believe this is optimistic. Here is my more honest estimate:

| Scenario | Realistic Accuracy |
|---|---|
| Unknown publisher, single-column, explicit "Abstract" heading, Arabic-numbered sections, "References" heading | ~85% — landmarks work, generic parser works |
| Unknown publisher, two-column, explicit headings | ~75% — column layout adds complexity, but landmarks still work |
| Unknown publisher, no "Abstract" heading (implicit abstract) | ~55% — landmark detection fails for abstract zone. Title and sections still work, but front-matter is confused. |
| Unknown publisher, unnumbered sections (bold headings only) | ~50% — landmark detection finds "References" and maybe "Abstract," but cannot find the first section heading. Body parsing degrades. |
| Unknown publisher, non-English headings | ~30% — landmark vocabulary is English-only. Falls back to pure geometry. |

**The honest overall estimate for truly unknown papers: ~65%, not 80%.**

The architecture's strength is that it **knows** when it is failing. The quality report will show low confidence. The paper will still render. But the claim that YAML profiles alone can add new publishers without code changes is only true when the unknown publisher follows the dominant archetype (explicit headings, numbered sections). For publishers that deviate from this archetype, a strategy file is needed — which is code.

**What must change:** The architecture should honestly document the expected accuracy degradation for each scenario. Do not promise 80% generic accuracy. Promise "always produces readable output" and "quality report always reflects actual confidence."

---

## 4. How Would Google Scholar / Semantic Scholar / Apple Approach This Differently?

### Google Scholar's Likely Approach: Inversion of Control

Google processes billions of documents. Their likely architecture inverts the pipeline:

1. **Start from the output schema.** Define exactly what fields they need: title, authors, abstract, venue, year, DOI.
2. **For each field, build an independent extractor.** Title extractor. Author extractor. Abstract extractor. These are independent modules that each scan the entire document.
3. **Each extractor runs in parallel** and produces a candidate with confidence.
4. **A reconciliation layer** combines the candidates, resolves conflicts, and produces the final output.

This is the **opposite** of a sequential pipeline. There is no reading order dependency. No front-matter vs. body distinction. Each extractor is a specialist that knows how to find one thing.

**Advantage:** Adding a new field does not require modifying the pipeline. Each extractor is independently testable. Failure in one extractor does not cascade.

**Disadvantage:** No structural context. The title extractor does not know where the abstract is. This makes it harder to resolve ambiguity.

**Takeaway for Paperly:** Consider whether TITLE detection really needs to happen before ABSTRACT detection. In the proposed pipeline, front-matter is parsed sequentially: title → authors → abstract. But if title detection fails, everything downstream fails. The Google approach — independent extractors that run in parallel and then reconcile — would prevent cascading failures.

### Semantic Scholar's Likely Approach: Two-Pass Architecture

Semantic Scholar (Allen AI) processes millions of papers. Their likely approach:

1. **Pass 1: Structure extraction.** Detect headings, sections, paragraphs. No semantic labels yet — just structural boundaries.
2. **Pass 2: Semantic labeling.** Given the structural boundaries, label each section. The abstract is the first section before "Introduction." The title is the largest text before the first section.

This is a **two-pass** architecture instead of the proposed **single-pass-with-landmarks.** The difference is subtle but important:

- In the proposed architecture, landmarks and classification happen in different stages but conceptually in one pass through the document.
- In a two-pass architecture, the first pass **only** identifies structural boundaries (where do blocks group? where are section breaks?). The second pass classifies within those boundaries.

**Advantage:** Pass 1 is publisher-independent. It uses only geometry and typography. Pass 2 uses Pass 1's boundaries to constrain classification. This is cleaner than having landmark detection and family detection as separate stages.

**Takeaway for Paperly:** The landmark detection stage is essentially Pass 1 of a two-pass architecture. But the proposed architecture does not commit to this framing. Making it explicit would clarify the design: "Pass 1 finds boundaries. Pass 2 labels the content within boundaries."

### Apple's Likely Approach: Data-Driven Threshold Learning

Apple would not hardcode thresholds like "title font size ≥ 1.4× body size." They would:

1. Parse 100 papers with manually verified golden labels.
2. For each feature (font size ratio, position, bold flag, etc.), compute the distribution of values for each semantic type.
3. Set thresholds at the decision boundary between distributions.
4. Store thresholds in a configuration file.
5. Re-derive thresholds when the corpus grows.

This is not machine learning — it is **corpus-driven threshold calibration.** The thresholds are deterministic once set, but they are derived from data rather than intuition.

**Takeaway for Paperly:** The golden dataset (5 papers with human-verified labels) should eventually be used not just for validation but for **threshold calibration.** When you have 50 golden papers, you can compute the actual distribution of title font size ratios across all families and set the threshold at the value that minimizes misclassification. This is a Phase 4+ concern, but the architecture should support it by keeping all thresholds in a single, documented location.

---

## 5. Challenge the Landmark Stage

### Can Landmark Detection Fail?

Yes. In at least seven ways.

**Failure 1: Implicit Abstracts (No "Abstract" Heading)**

Your own observations document this. ACM single-column papers (Spanner, BigTable, Teaching Ethics) have no "Abstract" heading. The abstract is an unlabeled paragraph. The landmark detector will not find an "Abstract" landmark for these papers.

Without the abstract landmark, the zone partitioning fails:
- The front-matter zone extends from the beginning of the document to the first section heading.
- Everything between the title and "1. Introduction" is classified as front-matter — including the abstract, CCS Concepts, Keywords, and ACM Reference Format.
- The front-matter parser must now separate abstract from non-abstract within this zone, without the benefit of a landmark.

**This is the most common landmark failure.** It affects ~40% of your current corpus. The architecture acknowledges it (Flaw 4, Question 12) but does not provide a concrete fallback.

**Required fallback:** When no "Abstract" landmark exists, the front-matter parser must use a **positional heuristic**: the first substantial prose block (≥ 40 words) after the author/affiliation region, before any metadata-like content (CCS, keywords), is the abstract. This heuristic must be built into the front-matter strategy, not the landmark detector.

**Failure 2: Non-English Headings**

The landmark vocabulary is English: "Abstract", "Introduction", "References", "Bibliography", "Acknowledgements." For German papers ("Zusammenfassung"), French papers ("Résumé"), or Chinese papers, no landmarks will be found.

This is acceptable for the initial scope (English CS papers) but must be documented as a known limitation, not hand-waved as "extensible landmark vocabulary."

**Failure 3: Old Scanned Papers**

The architecture says "Do not support scanned PDFs." But some papers in the corpus may be digitally-born PDFs that were later re-digitized or converted in ways that degrade text quality. The TCP Congestion paper (1988) and the UNIX paper (1974) are old enough that their PDF versions may have OCR artifacts, non-standard fonts, or broken Unicode.

Landmark detection relies on exact text matching. If "References" is OCR'd as "Referenoes" or "Ref erences" (with a space), the landmark is missed. The architecture needs a fuzzy matching layer for landmark text, or at least an edit-distance tolerance.

**Failure 4: Supplementary Material**

Some papers have supplementary material appended after the references. This material may have its own sections, its own "Abstract" (for a supplementary paper), and its own references. The landmark detector would find multiple "References" landmarks — which one is the real one?

**Required handling:** The first "References" landmark marks the end of the body zone. Any content after the references zone is classified as APPENDIX or supplementary material. The landmark detector should not search for additional landmarks after the first "References."

**Failure 5: Anonymous Submissions**

Conference submissions under double-blind review often:
- Replace author names with "Anonymous"
- Remove affiliations entirely
- Remove conference name / publisher strings

The landmark detector will still work (it does not depend on author/publisher information). But the family detector will fail — no publisher strings, no copyright blocks. The paper falls to GENERIC.

This is acceptable behavior. Document it.

**Failure 6: Papers Without Section Numbers**

Nature, Science, and some journal papers use **unnumbered bold headings** instead of numbered sections. The landmark "1. Introduction" or "1 INTRODUCTION" will not match "Introduction" (bold, no number).

The landmark detector must also recognize unnumbered heading patterns: a short block (< 60 characters), bold or large font, consisting of known heading words ("Introduction", "Methods", "Results", "Discussion", "Conclusion").

**This requires font information, not just text matching.** The architecture claims landmarks are "high-confidence, publisher-independent, and position-independent" and "can be detected with simple text matching." This is incorrect for unnumbered headings. Font analysis is required.

**Failure 7: Merged Blocks**

Per section 2B above, PyMuPDF may split "Abstract" across two blocks if the formatting changes mid-word (unlikely for "Abstract" but possible for "1. Introduction" where the number and text have different formatting). If the block says "1." and the next block says "Introduction", neither block matches the landmark pattern for "1. Introduction."

**Required mitigation:** Landmark detection should operate on the merged/reconstructed blocks, not the raw PyMuPDF blocks. This creates a dependency: block merging must happen before landmark detection. The architecture currently places text cleanup (Stage 5) before landmarks (Stage 7), but text cleanup does not include block merging (see gap 2A).

---

## 6. Challenge Family Detection

### Should Family Detection Happen Before Parsing?

The architecture assumes: detect family → select strategy → parse.

**The problem:** Family detection uses signals that overlap with parsing outputs. Specifically:

- **Section numbering style** is a family signal. But detecting section numbering requires finding section headings, which is a parsing operation.
- **Font fingerprint** requires analyzing the dominant body font, which requires distinguishing body text from headings — again a parsing operation.
- **Page structure fingerprint** requires knowing where the title, authors, and abstract are — which is what parsing determines.

This is a chicken-and-egg problem. Family detection needs parsing results. Parsing needs family detection results.

### Would Iterative Refinement Work Better?

Consider a two-iteration approach:

**Iteration 1: Quick pass.**
- Use only Tier 1 signals (publisher strings, copyright blocks) for family detection.
- Use only landmarks for zone partitioning.
- Run the generic parser to get a rough classification.

**Iteration 2: Refined pass.**
- Use the rough classification to compute additional signals (font fingerprint, section numbering style, page structure).
- Re-run family detection with all signals.
- If the family changed, re-run the appropriate family strategy.
- If the family did not change, keep the Iteration 1 output.

**Advantage:** Family detection is more accurate because it has access to parsing results. Parsing is more accurate because it has access to a refined family.

**Disadvantage:** Two passes through the document. More complex pipeline. Harder to debug.

**My assessment:** Iterative refinement is theoretically superior but practically unnecessary for the initial scope. Here is why:

For 22 of 26 papers, Tier 1 signals (publisher strings) are sufficient. The 4 papers where Tier 1 fails (TCP Congestion, End-to-End, UNIX, Hyperloop) are unusual enough that they can be handled by the generic parser with acceptable quality.

The iterative approach becomes valuable when you have 500+ papers and 15+ families, and Tier 1 signals alone are insufficient for 30%+ of papers. At that point, the cost of two passes is justified by the accuracy improvement.

**Recommendation:** Design the architecture to support iterative refinement in the future, but implement single-pass detection now. Concretely: make the family detector callable with an optional "preliminary classification" argument. Initially, this argument is always empty. Later, it can be populated by a first-pass parser.

---

## 7. Challenge the Generic Parser

### Is It Really Capable?

The architecture claims the generic parser handles unknown publishers at 80%+ accuracy using landmarks only. I outlined in Section 3 why this is optimistic. Let me be more specific about where it will fail.

**Failure Scenario A: Implicit Abstract + No Section Numbers**

A Nature-style paper with no "Abstract" heading and unnumbered bold headings. The generic parser:
- Finds no "Abstract" landmark → cannot partition front-matter from body
- Finds no "1. Introduction" landmark → cannot determine where body starts
- Finds "References" landmark → can partition body from references

Result: The entire document from the title to "References" is one undifferentiated zone. The parser falls back to pure geometry: largest block = title, first prose = abstract, everything else = PARAGRAPH. Sections are not detected.

This is a real failure mode for Nature, Science, PNAS, and many biomedical journal papers.

**Failure Scenario B: Multi-Column Front-Matter**

An IEEE paper where the author block is arranged in a multi-column layout within the front-matter. The author names are in three columns across the page. The reading order algorithm, which is designed for body text columns, may interleave the author columns incorrectly.

The generic parser does not account for multi-column front-matter. It assumes front-matter is single-column (spanning the full width).

**Failure Scenario C: Papers Starting with a Quotation**

Some papers begin with an epigraph or quotation before the title. The generic parser assumes the largest text on page 1 is the title. If the epigraph is in a large decorative font, it becomes the "title."

**My overall assessment of the generic parser:** It will work well for the dominant archetype (explicit headings, numbered sections, standard front-matter order). This covers arXiv, NeurIPS, ICML, ICLR, ACL, and similar venues — probably 60%+ of CS papers. For the remaining 40%, it will produce degraded but usually readable output.

**Recommendation:** Do not oversell the generic parser. Set expectations: "The generic parser produces readable output for all papers and high-quality output for papers with explicit structural headings." Then build family strategies for the common deviations.

---

## 8. Challenge the Universal Semantic Grammar

### Are There Missing Types?

**Yes. At least two.**

**Missing: LIST_ITEM**

Academic papers frequently contain bulleted or numbered lists within sections. These are not paragraphs — they have distinct visual formatting (indentation, bullets, numbers). The current grammar classifies them as PARAGRAPH, which is technically correct but loses structural information.

A reader application might want to render lists differently from prose paragraphs. Adding LIST_ITEM to the grammar allows this without retrofitting.

**Missing: ALGORITHM / CODE_BLOCK**

Computer science papers frequently contain pseudocode, algorithm descriptions, and code listings. These are neither paragraphs nor equations. They are distinct semantic entities with specific rendering requirements (monospace font, line numbers, syntax highlighting).

Currently, they would be classified as PARAGRAPH (if they look like text) or EQUATION (if they have unusual characters). Neither is correct.

**Whether to add these now:** LIST_ITEM is common enough that it should be in the grammar from the start. ALGORITHM is domain-specific (CS papers) and can be deferred to Phase 3B.

### Should FRONT_MATTER Exist?

**FRONT_MATTER is a design smell.** It exists because the architect could not define what CCS Concepts, General Terms, and ACM Reference Format are. Instead of modeling them, the architecture sweeps them into a catch-all bucket.

The problem: FRONT_MATTER will become a garbage collector. Anything the parser cannot classify in the preamble goes into FRONT_MATTER. Over time, FRONT_MATTER will contain:
- CCS Concepts
- General Terms
- Keywords that were not detected
- ACM Reference Format blocks
- Conference metadata
- DOI blocks
- Short author lines that were not identified
- Stray publisher logos

The renderer cannot usefully display a FRONT_MATTER block because it does not know what it is.

**However:** The alternative is worse. Defining PUBLISHER_METADATA, CCS_CONCEPTS, GENERAL_TERMS, ACM_REFERENCE, DOI, and CONFERENCE_INFO as separate semantic types creates a grammar that is specific to ACM papers and meaningless for arXiv papers.

**My assessment:** FRONT_MATTER is the correct pragmatic choice. It is the "I don't know, but it's not body text" category. The renderer should display it in a collapsed metadata section — visible on demand, hidden by default. Accept that this is an imperfect part of the grammar and move on.

### Should TITLE Be Mandatory?

The architecture says "the only hard requirement is TITLE." The invariant states "Exactly one TITLE."

**Edge case: Papers that genuinely have no title.** Anonymous submission templates sometimes have "SUBMISSION #1234" as the title-like block, or the title field is blank. Technical reports may have only a report number. Dataset papers may have the dataset name but no paper title.

**My recommendation:** TITLE remains mandatory, but the invariant is softened from "exactly one TITLE" to "at least one TITLE candidate." If the parser cannot identify a title with confidence > 0.5, it uses the first substantial text block on page 1 as a fallback title with a low-confidence flag. The quality report notes "title detected by position only."

### Should AUTHOR Nesting Include AFFILIATION?

The grammar proposes:

```
AUTHORS
└── AUTHOR
    └── AFFILIATION (optional)
```

This nesting implies a 1:1 mapping between authors and affiliations. In reality:
- Some papers have one shared affiliation for all authors.
- Some papers have numbered affiliations mapped to authors by superscript.
- Some papers list affiliations separately from authors.

**Recommendation:** Flatten the grammar. AUTHORS and AFFILIATIONS are sibling nodes, not parent-child. Let the renderer decide how to associate them.

```
├── AUTHORS
├── AFFILIATIONS (optional)
```

The current [models.py](file:///c:/Users/mayur/OneDrive/Desktop/Coding/Paperly/extractor/models.py) already does this correctly — `SemanticDocument` has `authors: List[SemanticBlock]` and `affiliations: List[SemanticBlock]` as parallel lists. The architecture document should match this.

---

## 9. Engineering Quality Evaluation

### Extensibility: **Strong**

The strategy pattern for family-specific parsing is the correct abstraction. Adding a new family requires:
1. A detection signal (publisher string or other)
2. A strategy file (or reuse of an existing strategy with different priors)
3. Regression snapshots for test papers

This is a well-defined extension protocol.

### Maintainability: **Moderate**

The separation between front-matter strategies (family-specific) and body parser (shared) is clean. However:

- **The body parser will still grow.** It handles section headings, captions, equations, footnotes, references. These are independent concerns packed into one module. When you need to fix equation detection, you edit the same file as footnote detection. Over time, body_parser.py will become its own monolith.

- **YAML profile changes are invisible.** If a YAML profile changes the `title_size_ratio` from 1.4 to 1.1, this affects parsing for every paper in that family. There is no test that catches this. Profile changes must be covered by regression snapshots — but only if the regression suite is always run.

### Debugging: **Strong**

The architecture's emphasis on audit logging, confidence scoring, and human-readable reason strings is excellent. The ability to trace "why was this block classified as AUTHORS?" through the audit log is the single most valuable debugging feature.

The visual diffing system (debug overlays) is also excellent and already partially implemented.

### Testing: **Strong in Design, Uncertain in Practice**

The five-layer validation pyramid is comprehensive. However:

- **Golden datasets require human effort.** Labeling every block in 5 papers is hours of work. Will this actually be done before implementation begins? Or will it be deferred and eventually forgotten?

- **Regression snapshots require discipline.** Every commit must re-run the full corpus. In practice, developers skip slow tests. The regression suite must run in under 30 seconds for 26 papers, or it will be ignored.

- **Semantic invariants can be too strict.** "Exactly one TITLE" is violated by papers with multi-line titles that the parser detects as two separate TITLE blocks. The invariant will flag this as a hard failure. The parser will need to either merge title blocks or soften the invariant. This tension will emerge during implementation.

### Future Contributors: **Moderate**

A new developer joining the project must understand:
1. The frozen pipeline (6 stages)
2. The new pipeline (8–10 stages)
3. The family detection system
4. The strategy pattern
5. The shared body parser
6. The YAML profile system
7. The validation pyramid
8. The semantic grammar

This is a significant learning curve. The architecture document helps, but the codebase also needs:
- A README in `extractor/` that explains the pipeline visually
- Inline documentation in each stage explaining its purpose and contract
- A "how to add a new family" guide

### Production Robustness: **Good**

The graceful degradation ladder (GENERIC → geometric-only → "everything is PARAGRAPH") ensures the parser never crashes. The quality report makes degradation visible. These are production-ready patterns.

### Long-Term Technical Debt: **Medium Risk**

The primary debt risks are:
1. **Threshold drift.** Hardcoded thresholds (1.4× body size for title, ≥ 40 words for abstract, etc.) become stale as the corpus grows. There is no mechanism to re-calibrate thresholds from data.
2. **Family proliferation.** If every publisher variation gets its own family, the family count will grow unbounded. The line between "this is a different family" and "this is a variant of an existing family" is unclear.
3. **YAML profile creep.** If profiles accumulate parameters over time (title_size_ratio, abstract_min_words, section_number_style, heading_bold_required, author_caps_required, ...), each profile becomes a mini-configuration-language with its own testing requirements.

---

## 10. How Would This Architecture Age at 1M Papers / 15 Publishers / 20 Years?

### What Would Become Painful

**1. Family Detection Ambiguity**

At 1M papers, you will encounter papers that match multiple families with similar confidence. An ACM paper published through IEEE Digital Library. A NeurIPS paper that uses the Springer LNCS template. A CVPR paper that looks exactly like an ICCV paper because they use the same template.

The family detector will return low-confidence results for these papers. The generic parser will handle them acceptably. But the quality report will flag them, creating a growing backlog of "ambiguous family" papers that no one reviews.

**2. Template Evolution Within Families**

ACM has changed their template 4+ times in 20 years. In the next 20 years, they will change it again. Each change creates a sub-variant within the family. The ACM_CLASSIC strategy that handles Spanner (2012) may not handle an ACM paper from 2040. You will need either sub-families or version-aware strategies.

**3. Landmark Vocabulary Growth**

As you add support for biomedical journals, physics journals, and social science publications, the landmark vocabulary will grow from 5 heading patterns to 50+. "Methods" and "Materials and Methods" and "Experimental Setup" and "Study Design" all mean the same thing. "Results" and "Findings" and "Experimental Results" are equivalent. Managing synonym groups will become its own maintenance burden.

**4. Regression Suite Runtime**

At 1M papers, you cannot run the full regression suite on every commit. You need tiered testing: golden papers on every commit, full corpus nightly. This infrastructure must be built eventually.

**5. Audit Log Storage**

An audit log for a 20-page paper might be 50–100 KB. At 1M papers, that is 50–100 GB of audit logs. If audit logs are stored alongside paper JSONs, storage becomes significant. The architecture should specify audit log retention policy.

### What Would Hold Up Well

1. **The frozen layers.** PDF parsing, coordinate normalization, layout detection — these are geometry, and geometry does not change. These will survive 20 years without modification.

2. **The universal semantic grammar.** Title, authors, abstract, sections, references — this structure has been stable in academic publishing for 50+ years. It will not change.

3. **The strategy pattern.** Adding new families by adding new strategies is a pattern that scales indefinitely.

4. **The quality report.** Knowing your confidence level on every paper is essential at any scale.

---

## 11. Five-Year Hindsight: Gratitude vs. Regret

### What You Would Thank the Original Engineers For

1. **Freezing the geometry layers.** The decision to validate and freeze Stages 1–4 before building semantic classification was the most important architectural decision. It gave the project a stable foundation and prevented the endless refactoring loop.

2. **The audit log.** Being able to trace every classification decision back to its reason string saves hours of debugging per paper.

3. **The semantic grammar as an interface boundary.** Everything downstream of the grammar (rendering, search, export) never needs to know about the parser. This decoupling allowed the reader application to evolve independently.

4. **Regression snapshots.** Being able to detect that "this commit changed the classification of block 47 in Spanner from ABSTRACT to FRONT_MATTER" prevents silent regressions.

5. **The quality report.** The first time a user submits a paper that parses at 0.55 confidence and you can immediately see why — that is when the quality report pays for itself.

### What You Would Regret

1. **Too many files too early.** If the `families/` directory was created with 10 files on day one but 7 of those files are 30-line stubs that all delegate to the generic parser, you created organizational overhead without value. You would wish you had started with `families.py` (one file) and split later.

2. **YAML profiles that nobody maintains.** If the YAML profile system was built in Phase 3A.1 but the team never grew beyond 1 developer, the profiles were maintained by the same person who could have maintained Python constants. The YAML system added indirection without adding capability.

3. **The "family" naming.** If family names are `ACM_CLASSIC`, `ACM_DOUBLE`, `ACM_MODERN`, you will eventually encounter a paper that is "ACM but does not fit any of these." You would wish you had named families after structural archetypes (`SINGLE_COL_IMPLICIT_ABSTRACT`, `DOUBLE_COL_EXPLICIT_ABSTRACT`) instead of publishers.

4. **Hardcoded thresholds without calibration infrastructure.** After parsing 10,000 papers, you would know that the optimal title size ratio is 1.25×, not 1.4×. But changing it breaks 200 regression snapshots. You would wish you had built threshold calibration from the golden dataset from the beginning.

5. **Not building paragraph merging earlier.** If paragraph merging was deferred to Phase 3B and everything in Phase 3A.1 was built on un-merged blocks, then Phase 3B's paragraph merging would change the block boundaries, which would invalidate every regression snapshot, every golden dataset label, and every family strategy. You would wish you had merged paragraphs in Phase 3A.1.

---

## 12. Revised Architecture

I am not rewriting the architecture. I am applying targeted corrections based on the pressure test above.

### Change 1: Consolidate Pipeline Stages

**Before:** 14 stages (6 frozen + 10 new, though minus 2 overlaps = 8 net new).

**After:** 10 stages (6 frozen + 6 new, though minus 2 overlaps = 4 net new stages + merged stages).

| # | Stage | Module | Notes |
|---|---|---|---|
| 1–4b, C | Frozen layers | `ingest.py`, `normalize.py`, `layout.py`, `consensus.py`, `ordering.py`, `corpus.py` | Unchanged |
| 5 | Pre-processing | `preprocess.py` | Text cleanup (NFC, ligatures, hyphens, whitespace) + Noise removal (headers, footers, boilerplate) + **Block merging** (adjacent same-font blocks into coherent units) |
| 6 | Document Identification | `identify.py` | Landmark detection + Family detection in one pass. Landmarks inform family detection directly. Output: landmarks, zone boundaries, family, family confidence. |
| 7 | Front-Matter Parsing | `front_matter.py` + `families.py` | Family-guided front-matter classification. `families.py` contains the generic strategy and, when needed, family-specific overrides. |
| 8 | Body Parsing | `body_parser.py` | Shared body parser with family-provided hints. Handles sections, captions, footnotes, equations, references. |
| 9 | Content Repair | `repair.py` | Hyphen repair (context-aware, cross-block) + Paragraph merging (within-section block stitching) + Reading continuity checks |
| 10 | Finalization | `finalize.py` | Tree assembly + Validation (invariants + confidence scoring + quality report) + JSON export. One file, three clear internal functions. |

**Justification:** This reduces the new file count from 10+ modules + a families directory to 6 modules. Each module is a meaningful, self-contained operation. The merges (cleanup + noise → preprocessing, landmarks + family → identification, tree + validation + export → finalization) combine stages that have tight data dependencies and no reason to run independently.

### Change 2: Add Block Merging to Pre-processing

**Rationale:** This is the most critical missing stage (Section 2A above). Block merging must happen before landmark detection and before semantic classification. It belongs in pre-processing because it is a structural reconstruction operation, not a semantic one.

**Block merging rules (architectural level, not implementation):**

- Two consecutive blocks on the same page, with matching font name, matching font size (within 0.5pt), matching bold flag, and vertical gap ≤ 1.5× the block height → merge into one block.
- The merged block inherits the bounding box that encloses both source blocks.
- Merging is conservative: if in doubt, do not merge. Unmerged blocks are safer than incorrectly merged blocks.

### Change 3: Simplify Family System

**Before:** `families/` directory with `registry.py`, `base_strategy.py`, 7 strategy files, and a `profiles/` subdirectory with YAML files.

**After:** `families.py` — one file containing:
1. The `FrontMatterStrategy` interface (a simple callable signature).
2. The `GENERIC` strategy (landmark-based front-matter parsing).
3. A registry dictionary mapping family IDs to strategies.
4. When the first family-specific strategy is needed, add it to this file.
5. When this file exceeds ~400 lines, split into a `families/` directory. Not before.

**YAML profiles deferred** until the strategy pattern is proven and the common parameters are known.

### Change 4: Strengthen the Generic Strategy

The generic strategy is the most important single piece of new code. It must handle:

1. **Papers with explicit "Abstract" heading:** Use the landmark to partition front-matter from body.
2. **Papers without "Abstract" heading:** Use the **positional rule** — first substantial prose block after title/authors, before first section heading = abstract.
3. **Papers with numbered sections:** Use number prefixes to detect section headings.
4. **Papers with unnumbered sections:** Use bold-font detection to identify headings (font analysis, not text matching).
5. **Papers with no detectable headings:** Classify everything as PARAGRAPH. Still readable.

The generic strategy must be the fallback for every family. If a family-specific strategy fails (raises an exception, returns zero classified blocks, or triggers an invariant violation), the pipeline re-runs with the generic strategy.

### Change 5: Document the Two-Pass Nature

The architecture should explicitly frame the pipeline as a two-pass system:

**Pass 1: Structure.** Pre-processing → Document Identification → Zone boundaries.
- This pass answers: "Where are the structural boundaries of this document?"
- It does not classify content. It finds boundaries.

**Pass 2: Semantics.** Front-Matter Parsing → Body Parsing → Content Repair → Finalization.
- This pass answers: "What is each block within each zone?"
- It uses the zone boundaries from Pass 1 to constrain classification.

This framing makes the architecture easier to understand and easier to extend. Pass 1 is publisher-independent (geometry + landmarks). Pass 2 is publisher-aware (family-guided classification).

### Change 6: Add LIST_ITEM to the Grammar

```
SECTION (recursive)
├── HEADING
├── PARAGRAPH
├── LIST_ITEM        ← NEW
├── FIGURE_REF
├── TABLE_REF
├── EQUATION_REF
└── SECTION (sub-section)
```

Detection: A block with indentation greater than the standard paragraph indentation, or a block starting with a bullet character (•, -, *, ◦) or a label pattern (a), b), c) / i), ii), iii)).

### Change 7: Flatten AUTHORS / AFFILIATIONS

**Before:**
```
AUTHORS
└── AUTHOR
    └── AFFILIATION
```

**After:**
```
├── AUTHORS
├── AFFILIATIONS (optional, sibling)
```

This matches the actual data model and avoids the false implication of 1:1 mapping.

### Change 8: Soften Invariants

**Before:** "Exactly one TITLE" — hard failure.

**After:** Invariants are classified as HARD (must never be violated) and SOFT (violation reduces quality score but does not fail the parse).

| Invariant | Type |
|---|---|
| At least one block classified | HARD |
| No block is unclassified | HARD |
| All input blocks present in output | HARD |
| At least one TITLE candidate | SOFT |
| At most one TITLE | SOFT |
| At least one AUTHORS block | SOFT |
| TITLE before AUTHORS (in reading order) | SOFT |
| ABSTRACT before first SECTION | SOFT |
| REFERENCES after last SECTION | SOFT |
| Total word count ≥ 90% of input | SOFT |

HARD invariants are data integrity constraints — the pipeline is producing garbage if they are violated. SOFT invariants are semantic expectations — real papers may violate them in edge cases.

### Change 9: Make Figure/Table Extraction Placement Explicit

Figure and table extraction is a separate concern from semantic classification. It should be architecturally placed as a **parallel operation** that runs alongside body parsing, not inside it.

```
After Document Identification:
    ├── Front-Matter Parsing (serial)
    ├── Body Parsing (serial)
    └── Figure/Table Extraction (can run in parallel)
        - Detect figure regions (raster + vector)
        - Detect table regions (find_tables + fallback)
        - Match captions from classified blocks
        - Rasterize and save images
```

The semantic tree references figures and tables via placeholders. The figure/table extraction produces the actual images. These are joined in the Finalization stage.

This placement is not a Phase 3A.1 implementation requirement — figures and tables are Phase 3B. But the architecture must reserve this slot now to prevent Phase 3B from requiring a pipeline restructuring.

### Revised Directory Structure

```
extractor/
├── __init__.py
├── __main__.py
│
├── # ─── FROZEN (Phase 3A.0) ───────────────────────
├── ingest.py
├── normalize.py
├── layout.py
├── consensus.py
├── ordering.py
├── corpus.py
│
├── # ─── NEW (Phase 3A.1) ──────────────────────────
├── preprocess.py       # Stage 5: cleanup + noise + block merging
├── identify.py         # Stage 6: landmarks + family detection
├── front_matter.py     # Stage 7: front-matter classification
├── families.py         # Family strategies (generic + specific)
├── body_parser.py      # Stage 8: body classification
├── repair.py           # Stage 9: hyphen repair + paragraph stitching
├── finalize.py         # Stage 10: tree assembly + validation + export
│
├── # ─── SUPPORTING ────────────────────────────────
├── models.py
├── confidence.py
├── debug.py
├── cli.py
│
├── # ─── VALIDATION ────────────────────────────────
├── golden/             # Human-verified block labels (5 papers)
└── snapshots/          # Regression snapshots (26 papers)
```

**Total new files:** 6 modules + `families.py` = 7 files.
**Compared to original proposal:** ~15+ files.
**Reduction:** 50%+ fewer files with identical functionality.

### Revised Execution Order

1. **Block merging** in `preprocess.py`. This must exist before anything else because all downstream stages depend on coherent blocks.
2. **Landmark detection** in `identify.py`. The highest-value single operation.
3. **Generic front-matter strategy** in `families.py`. Must be excellent standalone.
4. **Body parser** in `body_parser.py`. Shared, configurable.
5. **Finalization** in `finalize.py`. Tree + validation + export.
6. **Golden dataset** for 5 papers. Must exist before family strategies are written.
7. **Regression snapshots** for all 26 papers.
8. **Family-specific strategies** added to `families.py` one at a time, in priority order, each validated against regression suite before the next is started.

---

## Summary of All Changes

| # | Change | Rationale |
|---|---|---|
| 1 | Consolidate 14 stages → 10 | Reduces overhead without reducing modularity |
| 2 | Add block merging to pre-processing | Most critical missing stage; prevents downstream misclassification |
| 3 | Start with `families.py` (one file) | Avoid premature directory structure; split when needed |
| 4 | Strengthen generic strategy | Must handle implicit abstracts and unnumbered sections |
| 5 | Frame as two-pass (structure → semantics) | Clarifies the architecture for contributors |
| 6 | Add LIST_ITEM to grammar | Common enough to justify first-class support |
| 7 | Flatten AUTHORS/AFFILIATIONS | Matches actual data model; avoids false 1:1 mapping |
| 8 | Soften invariants (HARD vs. SOFT) | Prevents false failures on edge-case papers |
| 9 | Reserve slot for figure/table extraction | Prevents Phase 3B from requiring pipeline restructuring |

---

> [!IMPORTANT]
> **The core architecture is sound.** The landmark-based zone partitioning, family-guided front-matter parsing, shared body parser, and quality reporting — these are correct architectural decisions. The changes above are refinements, not rewrites. They remove premature abstraction, fill critical gaps (block merging), and simplify the implementation path.
>
> The revised architecture has fewer files, fewer stages, fewer abstractions, and the same conceptual power. It is ready for implementation.

---

*End of Pressure Test.*
