# EXP-11 — Smallest Behavior-Changing Experiment
*Surgical Invariant Injection*

## 1. Exact Hypothesis Being Tested
By artificially overriding `is_outlier = True` for any group in the Body that strictly matches a Lexical Section Regex and differs from the Universal Body Class, we can safely bypass the Landmark "local maxima" failure (which drops smaller-font headers) and completely recover the missing Spanner section headers without triggering a single regression in any other paper.

## 2. Why Existing Evidence Justifies This
*   **PIP-003 / EXP-01** proved Landmark mathematically misses Spanner headers.
*   **EXP-10** proved that `class != ubc AND SECTION_REGEX` perfectly identifies these missing headers with 94% precision.
*   **Implementation Impact Analysis** proved that `semantic.py` blindly trusts `is_outlier` to mean "evaluate me". 
By simply lying to the Semantic parser and telling it the valid regex candidates *are* outliers, we trick it into correctly resolving them using its existing fallback logic, bypassing the architectural flaw in 2 lines of code.

## 3. Exact Code Location
`extractor/semantic.py`, line 139, immediately inside the `if state == ParserState.BODY_PARSE:` block, right before the `if is_outlier:` check.

## 4. Before Control Flow
```python
        if state == ParserState.BODY_PARSE:
            if is_outlier:
                if re.match(r'^(?:\d+\.?\s*)?References?\s*$', text_lower):
```

## 5. After Control Flow
```python
        if state == ParserState.BODY_PARSE:
            # EXP-11: Surgical bypass for Landmark local maxima failure
            if group.typography_class != universal_body_class and (re.match(r'^\d+\.?\s+[a-z]', text_lower) or re.match(r'^\d+\.\d+\.?\s+[a-z]', text_lower)):
                is_outlier = True
                
            if is_outlier:
                if re.match(r'^(?:\d+\.?\s*)?References?\s*$', text_lower):
```

## 6. Expected Improvement
Spanner (and any other paper with smaller-font headers) will suddenly begin extracting its Section Headers ("1. INTRODUCTION", "2. IMPLEMENTATION") into the final hierarchical JSON, completely closing the PIP-003 extraction gap.

## 7. Expected Regression
**Zero.** 
Because we apply a highly restrictive regex (`^\d+\.?\s+[a-z]`) combined with a negative check against the body class (`class != ubc`), we cannot accidentally admit noise. Furthermore, we intentionally do *not* attempt to fix the existing 69 false-positive outliers, preserving the exact current behavior for BERT and Attention to guarantee isolation of variables.

## 8. Rollback Plan
Delete the 2 inserted lines of python code. 

## 9. Which Benchmark Papers Validate It
*   `Spanner.pdf` (Should gain missing headers)

## 10. Which Benchmark Outputs Would Falsify The Hypothesis
The hypothesis is falsified if:
*   Spanner headers still do not appear in the JSON output.
*   BERT or Attention Is All You Need outputs change in any way (proving the regex/ubc heuristic is less restrictive than calculated in EXP-10).
