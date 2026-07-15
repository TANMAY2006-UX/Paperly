# Architecture Review 001 — Evidence Synthesis
*Synthesis of Empirical Findings from PIP-003, EXP-01, EXP-06, EXP-07, EXP-08, and EXP-09*

---

## Task 1 — Experimentally Verified Facts

**Fact 1: Landmark's local maxima heuristic fails on "valleys".**
*   **Experiment:** PIP-003
*   **Evidence:** Section headers in Spanner use a larger typography class ID (smaller font) than body text. The math `(curr <= prev and curr <= next)` rejects them because they are local minima, not maxima.
*   **Confidence:** High (Proven by direct trace).

**Fact 2: `is_outlier` misses the majority of structural data.**
*   **Experiment:** EXP-06
*   **Evidence:** Only 29.65% of true structural objects trigger `is_outlier`. 51.76% fall into Set B (discarded by Landmark, but typographically distinct). 18.59% fall into Set C (physically identical to body).
*   **Confidence:** High (Proven by candidate enumeration).

**Fact 3: Structural headers and tabular noise are physically inseparable in Set B.**
*   **Experiment:** EXP-07
*   **Evidence:** 103 True Positives and 575 False Positives share overlapping distributions for block count, character length, physical bolding, and page position.
*   **Confidence:** High.

**Fact 4: Existing Lexical RegEx perfectly recovers 30% of missed Set B objects.**
*   **Experiment:** EXP-08
*   **Evidence:** Applying `SECTION_REGEX` and `SUBSECTION_REGEX` directly perfectly recovers 31 valid headers while rejecting false positives.
*   **Confidence:** High.

**Fact 5: Front Matter objects are lexically inseparable from tabular noise.**
*   **Experiment:** EXP-08
*   **Evidence:** 70% of missed structural objects (Authors, Titles) have no exact regex signature, no reliable numeric ratio, and are lexically identical to short table values.
*   **Confidence:** High.

**Fact 6: Parser State mathematically separates Front Matter from Body.**
*   **Experiment:** EXP-09
*   **Evidence:** 90 valid Front Matter objects are evaluated in `FRONT_MATTER_PARSE`. They never compete against the 425 table values that only appear in `BODY_PARSE`.
*   **Confidence:** High.

---

## Task 2 — Unproven Hypotheses

*   **Hypothesis A:** Semantic should ignore the `is_outlier` gate entirely and evaluate all Set B candidates natively.
*   **Hypothesis B:** Spatial Intersection (Geometry) is sufficient to break the final Front Matter ambiguity.
*   **Hypothesis C:** The universal body class calculation is resilient enough to act as the primary structural boundary without `is_outlier`.
*   **Hypothesis D:** Landmark should be completely removed from the pipeline.

---

## Task 3 — Dependency Graph

**Hypothesis A: Semantic should ignore the `is_outlier` gate**
*   **Supported by:** Fact 2 (is_outlier misses 70%), Fact 4 (Semantic regex perfectly recovers headers), Fact 6 (Parser state isolates noise).
*   **Contradicted by:** None.
*   **Missing Evidence:** Will bypassing the gate introduce catastrophic false positives from Set C (body text)?

**Hypothesis B: Spatial Intersection resolves Front Matter**
*   **Supported by:** Fact 3 (Physics fails), Fact 5 (Lexical fails), Fact 6 (Parser state isolates the remaining 90 vs 150 conflict).
*   **Contradicted by:** None.
*   **Missing Evidence:** We have not experimentally measured the spatial relationships of the Front Matter objects.

---

## Task 4 — Architectural Evaluation

**1. Layout / Ordering / Assembly**
*   **Proven Correct Behaviour:** Accurately extracts physical text, geometry, and constructs deterministic text blocks and vectors.
*   **Proven Limitations:** None observed.
*   **Unknowns:** None.

**2. Landmark**
*   **Proven Correct Behaviour:** Successfully identifies absolute layout anchors (Title, References boundary).
*   **Proven Limitations:** The `is_outlier` (local maxima) logic is fundamentally mathematically incorrect for valleys (smaller font headers) and discards 70% of structural data.
*   **Unknowns:** Can Landmark be redefined strictly as a bounding mechanism rather than a candidate generator?

**3. Semantic**
*   **Proven Correct Behaviour:** Parser state machine perfectly isolates structural domains (Front Matter vs Body). Lexical regexes are perfectly precise when given the chance to evaluate.
*   **Proven Limitations:** It is currently blind to 70% of the paper because it obeys the `is_outlier` contract.
*   **Unknowns:** How does Semantic handle spatial geometry (currently absent from its logic)?

---

## Task 5 — Engineering Decision Record

1.  **Issue:** Landmark local maxima heuristic rejects valid headers.
    *   **Classification:** **C. Architectural Limitation** (The local maxima assumption is fundamentally incompatible with the reality of smaller-font section headers).
2.  **Issue:** Semantic cannot parse un-flagged structural objects.
    *   **Classification:** **B. Contract Bug** (Semantic trusts the `is_outlier` boolean as an absolute gatekeeper, despite having superior lexical and state-based evidence to evaluate Set B itself).
3.  **Issue:** Authors and unnumbered titles are indistinguishable from noise using text/physics.
    *   **Classification:** **C. Architectural Limitation** (The pipeline discards or ignores spatial geometry which is required to resolve this).

---

## Task 6 — Unresolved Engineering Questions

1.  If Semantic evaluates *all* Set B objects (ignoring `is_outlier`), does the combination of Parser State (EXP-09) and Lexical RegEx (EXP-08) correctly reconstruct the Body?
2.  Does the universal body class (UBC) act as a sufficient and deterministic boundary to prevent Set C from contaminating Semantic?
3.  If we evaluate the spatial geometry (bounding box intersections) of Front Matter objects, does it perfectly separate Authors from Abstract noise?
4.  Can Landmark's contract be safely reduced to *only* detecting the ANCHOR (Title) and the END (References) without acting as a candidate generator?

---

## Task 7 — Final Conclusion

Based strictly on verified evidence:

**B. Requires interface refinement**

**Evidence:**
The core extraction algorithms (Layout, Ordering, Assembly, Semantic State Machine, Lexical Regex) are proven to be highly precise and fundamentally sound. The failure originates almost entirely at the *interface* between Landmark and Semantic. 

Landmark computes an overly aggressive boolean (`is_outlier`) based on a flawed physical assumption (local maxima). Semantic blindly trusts this boolean, discarding its own superior contextual and lexical evidence. By refining the interface—specifically, by removing the `is_outlier` gate and allowing Semantic to evaluate candidate sets directly using its state machine—the architecture mathematically possesses enough information to succeed without requiring a complete redesign.
