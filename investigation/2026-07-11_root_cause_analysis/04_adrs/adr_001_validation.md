# ADR-001 Validation
*Implementation Readiness Review*

## Part 1 — Proposal Review

**Proposal 1: Evaluate Set B Directly**
*   **Experimental Proof:** EXP-06 proved `is_outlier` drops 70% of structural data. EXP-08 proved regex can recover 30% of Set B (headers). EXP-09 proved parser state isolates Set B noise.
*   **Merely Suggests:** Suggests that evaluating Set B is safe.
*   **Assumptions:** Assumes the Universal Body Class (UBC) computation is flawless. Assumes Semantic can safely reject the 575 False Positives in Set B without exploding.

**Proposal 3: Reduce Landmark Responsibility**
*   **Experimental Proof:** PIP-003 and EXP-01 proved local maxima math is mathematically incompatible with valleys (smaller font headers).
*   **Merely Suggests:** Suggests Landmark should only detect Anchors/Endpoints.
*   **Assumptions:** Assumes Semantic is capable of absorbing the full candidate generation workload.

---

## Part 2 & 3 — Implementation Alternatives & Challenges

**Proposed Milestone 1:** Change the gate in `semantic.py` from `if is_outlier:` to `if is_outlier or group.typography_class != universal_body_class:`.

**Challenge:** Is this the *only* implementation? No.
*   **Alternative 1 (Regex Gate):** `if is_outlier or SECTION_REGEX.match(text):`
*   **Alternative 2 (State Gate):** `if is_outlier or (state == ParserState.BODY_PARSE and typography_class != ubc):`
*   **Alternative 3 (Total Bypass):** Remove the gate entirely and evaluate every single group natively through the state machine.
*   **Alternative 4 (Strict Regex Resolution):** Modify the `else` block inside `BODY_PARSE` to explicitly require `SECTION_REGEX` before pushing a new section to the stack.

---

## Part 4 — Implementation Risk

If we implement the proposed milestone `if is_outlier or class != ubc`:
*   **Invariant Changes:** Semantic currently expects the `if is_outlier:` block to filter out all unbolded inline text and tables.
*   **Parser Assumptions Change:** The parser assumes that *any* group entering the `is_outlier` fallback branch is a Section Header.
*   **Benchmark Regression:** **Catastrophic Failure Risk.** Attention Is All You Need and BERT will violently regress.
*   **Validating Success:** Spanner (Header recovery).

---

## Part 5 — Hidden Coupling

**Critical Discovery:** Proposal 1 secretly depends on an undocumented assumption in `semantic.py`.
Looking at `semantic.py:150` inside `BODY_PARSE`:
```python
            if is_outlier:
                # ... checks for references, appendix, body class, caption ...
                else:
                    # Body Section Header Resolution
                    while len(section_stack) > 1: ...
                    new_section = SemanticNode(...)
```
The parser **blindly assumes** that any unhandled outlier is a valid Section Header. 

If we admit Set B (which EXP-08 proved contains 575 False Positives, including Inline Bold and Table Values) into this block by changing the gate to `if is_outlier or class != ubc:`, the parser will immediately promote every bold word and every table cell into a top-level Section Header. 

Proposal 1 is dangerously coupled to the Section Stack assumption. Bypassing the gate requires explicitly checking Lexical Regex (`SECTION_REGEX`) before modifying the stack.

---

## Part 6 — Single Responsibility Violation

The proposed Milestone 1 violates single responsibility. It attempts to:
1.  Open the Set B gate.
2.  Rely on existing fallback logic to process Set B.

This must be split.
*   **Action A:** Modify the fallback logic to require explicit proof (regex) before creating a Section Header.
*   **Action B:** Open the Set B gate to feed candidates into that logic.

---

## Part 7 — Final Implementation Readiness Report

**Milestone 1: Body Parse Structural Recovery (Bypass `is_outlier`)**
*   **Classification:** **REJECT**
*   **Reasoning:** The proposed code change (`if is_outlier or class != ubc:`) will cause catastrophic regressions because of hidden coupling. `semantic.py` currently assumes any unhandled outlier is a Section Header. Admitting Set B will promote 575 false positives (Table Values, Inline Math, Bold Text) into Section Headers. The code must be rewritten to explicitly demand lexical proof (`SECTION_REGEX`) before modifying the parser stack.

**Milestone 2: Front Matter Geometry Experiment**
*   **Classification:** **READY**
*   **Reasoning:** This is a pure telemetry experiment to measure the final missing dimension (spatial geometry) for resolving Authors vs Abstract noise. It touches no production code and has zero regression risk.

**Conclusion:** ADR-001 Milestone 1 is rejected for implementation until the hidden coupling in the Semantic parser is addressed. Do not proceed to implementation.
