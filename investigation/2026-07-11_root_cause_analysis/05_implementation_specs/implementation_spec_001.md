# Implementation Specification 001
*State Transition De-Multiplexing*

## 1. Control Flow Diagrams

### Current Control-Flow (`BODY_PARSE`)
```text
IF state == BODY_PARSE:
    IF is_outlier:  <-- [MULTIPLEXED GATE]
        IF matches "References":
            state = REFERENCES_PARSE
        ELIF matches "Appendix":
            state = APPENDIX_PARSE
        ELIF class == ubc:
            add Paragraph
        ELIF matches Caption:
            add Caption
        ELSE:
            add Section Header  <-- [DANGEROUS FALLBACK]
    ELSE:
        IF matches Caption:
            add Caption
        ELSE:
            add Paragraph
```

### Proposed Control-Flow (`BODY_PARSE`)
```text
IF state == BODY_PARSE:
    # 1. Isolated State Transitions
    IF is_outlier AND matches "References":
        state = REFERENCES_PARSE
    ELIF is_outlier AND matches "Appendix":
        state = APPENDIX_PARSE
    ELSE:
        # 2. Isolated Candidate Selection
        IF is_outlier:  <-- [ISOLATED GATE]
            IF class == ubc:
                add Paragraph
            ELIF matches Caption:
                add Caption
            ELSE:
                add Section Header
        ELSE:
            IF matches Caption:
                add Caption
            ELSE:
                add Paragraph
```

---

## 2. Unified Diff Plan

The refactoring applies exclusively to the `state == ParserState.BODY_PARSE` block in `extractor/semantic.py`.

```diff
-        if state == ParserState.BODY_PARSE:
-            if is_outlier:
-                if re.match(r'^(?:\d+\.?\s*)?References?\s*$', text_lower):
-                    state = ParserState.REFERENCES_PARSE
-                    # Re-evaluate under REFERENCES_PARSE
-                elif re.match(r'^(?:\d+\.?\s*)?Appendices|Appendix\b', text_lower):
-                    state = ParserState.APPENDIX_PARSE
-                    # Re-evaluate under APPENDIX_PARSE
-                elif group.typography_class == universal_body_class:
-                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.PARAGRAPH, group=group))
-                elif _is_caption(group):
-                    section_stack[-1].children.append(SemanticNode(node_type=SemanticType.CAPTION, group=group))
-                else:
-                    # Body Section Header Resolution
-                    while len(section_stack) > 1:
...
-            else:
...
+        if state == ParserState.BODY_PARSE:
+            # 1. State Transitions (Preserves is_outlier requirement to maintain exact current behavior)
+            if is_outlier and re.match(r'^(?:\d+\.?\s*)?References?\s*$', text_lower):
+                state = ParserState.REFERENCES_PARSE
+            elif is_outlier and re.match(r'^(?:\d+\.?\s*)?Appendices|Appendix\b', text_lower):
+                state = ParserState.APPENDIX_PARSE
+            else:
+                # 2. Structural Candidate Selection
+                if is_outlier:
+                    if group.typography_class == universal_body_class:
+                        section_stack[-1].children.append(SemanticNode(node_type=SemanticType.PARAGRAPH, group=group))
+                    elif _is_caption(group):
+                        section_stack[-1].children.append(SemanticNode(node_type=SemanticType.CAPTION, group=group))
+                    else:
+                        # Body Section Header Resolution
+                        while len(section_stack) > 1:
...
+                else:
...
```

---

## 3. Behavior Preservation Justification

*   **Why it preserves behavior:** The exact same boolean logic is evaluated in the exact same order. Previously, if `is_outlier` was true and it matched "References", it changed state and skipped the `elif` blocks. Now, it matches the compound `if`, changes state, and skips the `else` block containing the rest of the logic. The outcome is mathematically identical.
*   **Which invariant it preserves:** The assumption that "References" must be an outlier to trigger a state transition, and the assumption that unhandled outliers become Section Headers.
*   **Which benchmarks validate it:** All benchmarks (Spanner, BERT, Attention) must produce byte-for-byte identical output after this change.
*   **Rollback Strategy:** `git checkout extractor/semantic.py`

---

## 4. Regression Checklist

- [ ] Does "References" correctly change the state to `REFERENCES_PARSE`?
- [ ] Are Section Headers still created for unhandled outliers?
- [ ] Are Captions and Paragraphs correctly routed regardless of the outlier flag?
- [ ] Does the `semantic.py` script pass python syntax validation?

---

## 5. Test Plan

1.  Execute `python scratch/check_results.py` on the `master` branch and record the exact node counts, header counts, and extracted JSON hashes for all 3 benchmarks.
2.  Implement the localized refactoring in `extractor/semantic.py`.
3.  Re-run `python scratch/check_results.py`.
4.  **Success Criterion:** The JSON output must be completely unchanged. The telemetry counts must match perfectly. This proves the architecture was safely decoupled without altering runtime behavior.
