# Implementation Impact Analysis
*Pre-Implementation Code Audit*

## Part 1 — Dependency Map (`is_outlier`)

The boolean `is_outlier` fundamentally controls the control flow in `semantic.py` across four parser states:

1.  **`FRONT_MATTER_PARSE` (Line 118)**
    *   Controls transition to `BODY_PARSE`.
    *   Controls creation of `ABSTRACT` node.
    *   Fallback: Creates `AUTHORS` node.
2.  **`BODY_PARSE` (Line 139)**
    *   Controls transition to `REFERENCES_PARSE`.
    *   Controls transition to `APPENDIX_PARSE`.
    *   Fallback: Pops `section_stack` and creates a `SECTION_HEADER` node (Line 150).
3.  **`REFERENCES_PARSE` (Line 176)**
    *   Controls transition to `APPENDIX_PARSE`.
    *   Fallback: Pops stack and creates new `REFERENCES` section node.
4.  **`APPENDIX_PARSE` (Line 191)**
    *   Fallback: Pops stack and creates new `APPENDIX` section node.

---

## Part 2 — Assumed Invariants

*   **Front Matter:** Assumes that the textual boundary between Abstract and Body will ALWAYS be a local maximum (outlier). Assumes any unhandled outlier is an Author.
*   **Body:** Assumes that the textual boundaries for References and Appendices will ALWAYS be local maxima (outliers).
*   **Body Fallback (Line 150):** Assumes that *any unhandled outlier in the body* is a Valid Section Header.
*   **References/Appendix:** Assumes that any unhandled outlier inside the bibliography is a sub-header.

---

## Part 3 — Behavior Change Analysis

If we replace `is_outlier` with `(typography_class != universal_body_class) AND (SECTION_REGEX matches)`:

*   **`FRONT_MATTER_PARSE`**: **HIGH RISK / BEHAVIOR CHANGE**. Front matter objects (Authors, Abstract) do not match `SECTION_REGEX`. If we apply this gate, Semantic will stop parsing Abstracts entirely.
*   **`BODY_PARSE` (Transitions)**: **HIGH RISK / BEHAVIOR CHANGE**. "References" and "Appendix" do not match `SECTION_REGEX` (which requires a leading number). The parser would permanently fail to transition to `REFERENCES_PARSE`.
*   **`BODY_PARSE` (Fallback Header)**: **SAFE CHANGE**. Replacing the blind fallback with the strict regex-gated invariant will flawlessly recover headers and reject noise.
*   **`REFERENCES_PARSE`**: **HIGH RISK / BEHAVIOR CHANGE**. 

---

## Part 4 — Implicit Assumptions

1.  **"Default else in Front Matter means Author"** (Line 129): Causes footnote markers to become Authors.
2.  **"Default else in Body means Section Header"** (Line 150): Causes table cells and inline bold text to become Section Headers if Landmark flagged them incorrectly.
3.  **"State Transitions require local maxima"**: The parser assumes it is impossible for the word "References" to appear in a font size identical to the body text. If it did, it wouldn't be an outlier, and the parser would never transition.

---

## Part 5 — Invariant Sufficiency

The EXP-10 invariant (`not_ubc AND BODY_PARSE AND SECTION_REGEX`) is **INSUFFICIENT** to completely replace `is_outlier`.

**What breaks?**
State Transitions. 
The current `semantic.py` multiplexes two entirely different responsibilities into the single `if is_outlier:` block:
1.  **State Transitions** (e.g., entering References).
2.  **Candidate Selection** (e.g., creating a Section Header).

The EXP-10 invariant perfectly solves Candidate Selection. It breaks State Transitions, because structural boundaries like "References" do not match `SECTION_REGEX`.

---

## Part 6 — Implementation Impact Matrix

| Code Block | Current Responsibility | Future Responsibility | Risk | Regression Probability |
| :--- | :--- | :--- | :--- | :--- |
| `BODY_PARSE` Transitions (Line 140-145) | Wait for `is_outlier` to detect "References" | Must be decoupled from `SECTION_REGEX` candidates. | **HIGH** | High (if inadvertently gated by `SECTION_REGEX`). |
| `BODY_PARSE` Header Fallback (Line 150-168) | Promotes any unhandled outlier to Section Header | Evaluate Set B candidates using `SECTION_REGEX`. | **LOW** | Low. (Recovers Spanner, prevents table fragmentation). |
| `FRONT_MATTER_PARSE` | Filter Authors/Abstracts via `is_outlier` | Unchanged (EXP-10 invariant does not apply here). | **NONE** | None. |

---

## Part 7 — Final Conclusion

Based on the explicit code paths in `semantic.py`, EXP-10's invariant:

**B. Requires localized refactoring**

**Evidence:**
We cannot use EXP-10's invariant as a "drop-in compatible" replacement for `if is_outlier:`. The `semantic.py` code currently tightly couples State Transitions (which use words like "References") with Structural Candidate Selection (which uses numbers like "1. Introduction") inside the exact same `if is_outlier:` block. 

To safely implement EXP-10's invariant, we must perform a localized refactoring of `BODY_PARSE`. We must split the `if is_outlier:` block into two independent checks:
1.  A check for State Transitions (which can continue to trust `is_outlier` for now).
2.  An explicit, isolated check for Section Headers using `(typography_class != universal_body_class) and (SECTION_REGEX)` to replace the dangerous fallback logic.
