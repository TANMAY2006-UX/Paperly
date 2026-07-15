# Investigation Summary

## Timeline of investigation
1. **PIP-003**: Root cause proof identifying Landmark's failure on Spanner's "valley" headers.
2. **EXP-01 & EXP-02**: Runtime instrumentation measuring massive false positive contamination (9.7:1) from Landmark's local maxima heuristic.
3. **EXP-06**: Candidate Set measurement showing Landmark drops 70% of valid structural candidates (Set B).
4. **EXP-07, EXP-08, EXP-09**: Separability analyses proving that physical traits are inseparable, but Lexical Regex + Parser State provides near-perfect separation for Body Headers.
5. **EXP-10**: Pattern mining to extract the definitive minimal deterministic invariant (`not_ubc` + `SECTION_REGEX`) to replace Landmark's Candidate Selection.
6. **ADR-001, ADR-001 Validation, ADR-002**: Architectural Decision Records defining proper compiler stage ownership and rejecting dangerous, coupled implementations.
7. **Implementation Spec 001 & EXP-11**: Designing the precise, surgically isolated experiment to test the structural invariant bypass without breaking current compiler assumptions.

## Questions investigated
*   Why is Spanner missing its section headers in the final JSON?
*   Is Landmark's local maxima heuristic structurally sound for candidate generation?
*   Can physical physics (geometry/boldness), lexical regex, or parser state separate structural noise from true headers in Set B?
*   Which compiler architectural stage truly owns Candidate Selection?

## Questions answered
*   Spanner misses headers because they are physically smaller (valleys, not local maxima), breaking the Landmark math.
*   Landmark's local maxima heuristic is fundamentally flawed for structural boundaries.
*   Physical attributes (boldness, bounding boxes) cannot separate noise from structure in Set B.
*   Lexical regex + Parser State perfectly recovers 30% of missed objects (Body Headers) with 94% precision.
*   `semantic.py`'s current logic heavily couples State Transitions with Candidate Selection.

## Hypotheses disproved
*   **Disproved:** Landmark is capable of identifying all structural candidates globally. (It misses 70%).
*   **Disproved:** `is_outlier` is a safe gatekeeper. (It admits 134 false positives, and the fallback assumes any unhandled outlier is a Section Header).
*   **Disproved:** Authors can be separated by text/physics alone.

## Hypotheses still open
*   Can Spatial Geometry resolve the Front Matter Author/Title ambiguity? (Awaiting experiment).
*   Does the EXP-11 surgical invariant bypass safely restore Spanner headers without regressing other papers? (Awaiting execution).

## Final evidence collected
*   **Candidate Enumeration:** Set A (Outliers) contains 29%, Set B (Non-UBC) contains 51%, Set C (UBC) contains 18% of structural data.
*   **False Outlier Contamination Ratio:** 9.7:1 false positives in the pipeline.
*   **Precise Lexical Separability:** Regex precision is 94% on Body Set B candidates.

## Current implementation status
*   **Frozen.** The investigation phase is complete. 
*   `semantic.py` currently contains a multiplexed State Transition / Candidate Selection flaw. 
*   Code modifications to decouple this flaw (Implementation Spec 001) and bypass the Landmark bug (EXP-11) have been strictly designed but not yet implemented.
