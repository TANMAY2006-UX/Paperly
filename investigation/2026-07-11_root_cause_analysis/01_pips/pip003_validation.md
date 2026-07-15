# PIP-003 Validation
*Execution Trace for "1. INTRODUCTION"*

## Exact TypographicGroup State
*   **raw text**: `"1. INTRODUCTION"`
*   **repr(text)**: `'1. INTRODUCTION'`
*   **typography_class**: `1` (or equivalent small integer representing physically large text)
*   **landmark classification**: `None`
*   **is_outlier**: `False`
*   **parser state before processing**: `ParserState.FRONT_MATTER_PARSE`

## Execution Trace (semantic.py)

1.  `if state == ParserState.FRONT_MATTER_PARSE:` $\rightarrow$ **Evaluates True**
2.  `if is_outlier:` $\rightarrow$ **Evaluates False**
3.  *(Jumps to `else` branch)*
4.  `if section_stack[-1].node_type == SemanticType.ABSTRACT:` $\rightarrow$ **Evaluates False** (Abstract node was never created because it also lacked an outlier token).
5.  *(Jumps to nested `else` branch)*
6.  `section_stack[-1].children.append(SemanticNode(node_type=SemanticType.AUTHORS, group=group))` $\rightarrow$ **Executed branch**

## Parser State After Processing
*   **parser state after processing**: `ParserState.FRONT_MATTER_PARSE`

---

## Conclusion

**Why was BODY_PARSE never entered?**

The earliest failing condition is **`if is_outlier:`** evaluating to `False`.

Because `semantic.py` defines that a smaller `typography_class` integer represents physically larger text, a section header like "1. INTRODUCTION" possesses a numerically smaller value (e.g., 1) than the body paragraphs surrounding it (e.g., 3). 

However, `landmarks.py` computes outliers by searching for mathematical local maxima (`curr_emp > prev_emp and curr_emp > next_emp`). Consequently, section headers act as mathematical local *minima* (e.g., `1 > 3` is `False`). Because "1. INTRODUCTION" fails the `landmarks.py` maximum inequality, it never receives an `OUTLIER` token. Without the token, the execution bypasses the structural regex validations entirely and degrades to the `AUTHORS` fallback.
