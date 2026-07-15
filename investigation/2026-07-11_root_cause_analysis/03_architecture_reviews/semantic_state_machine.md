# Semantic State Machine Verification
*Deterministic Parser Logic*

## 1. State Verification Rules

### `TITLE_SEARCH`
*   **1. Legal Objects**: `TITLE`, `NOISE`
*   **2. Impossible Objects**: `ABSTRACT`, `SECTION_HEADER`, `CAPTION`, `REFERENCES`, `AUTHORS`, `AFFILIATION`, `PARAGRAPH`
*   **3. Transition Evidence**: A TypographicGroup flagged with `is_anchor == True`. (Transitions to `FRONT_MATTER_PARSE`).
*   **4. Insufficient Evidence**: Any block without the Anchor landmark.
*   **5. Same State**: All non-anchor blocks create a `NOISE` node while remaining in `TITLE_SEARCH`.

### `FRONT_MATTER_PARSE`
*   **1. Legal Objects**: `ABSTRACT`, `AUTHORS`, `AFFILIATION`, `PARAGRAPH` (only as abstract body)
*   **2. Impossible Objects**: `TITLE`, `REFERENCES`, `SECTION_HEADER`, `CAPTION`
*   **3. Transition Evidence**: `is_outlier == True` AND (the stack already contains an `ABSTRACT` node OR the text matches a standard body header regex). (Transitions to `BODY_PARSE`).
*   **4. Insufficient Evidence**: Any `is_outlier == True` that is neither "Abstract" nor a valid Body section header (e.g., author names, affiliations, emails).
*   **5. Same State**: 
    *   `is_outlier == True` AND text is "Abstract" $\rightarrow$ Create `ABSTRACT` node.
    *   Insufficient outlier $\rightarrow$ Create `AUTHORS` (or `AFFILIATION`) node.

### `BODY_PARSE`
*   **1. Legal Objects**: `SECTION_HEADER`, `SECTION`, `PARAGRAPH`, `CAPTION`
*   **2. Impossible Objects**: `TITLE`, `ABSTRACT`, `AUTHORS`, `AFFILIATION`
*   **3. Transition Evidence**: `is_outlier == True` AND text strictly matches "References" or "Bibliography". (Transitions to `REFERENCES_PARSE`).
*   **4. Insufficient Evidence**: `is_outlier == True` representing unhandled formatting (e.g., bold table data) or standard section headers.
*   **5. Same State**:
    *   Insufficient outlier $\rightarrow$ Create `SECTION_HEADER` node.
    *   Matches caption regex $\rightarrow$ Create `CAPTION` node.
    *   Matches `universal_body_class` $\rightarrow$ Create `PARAGRAPH` node.

### `REFERENCES_PARSE`
*   **1. Legal Objects**: `REFERENCES`
*   **2. Impossible Objects**: `TITLE`, `ABSTRACT`, `AUTHORS`, `AFFILIATION`, `CAPTION`, `PARAGRAPH`
*   **3. Transition Evidence**: `is_outlier == True` AND text strictly matches "Appendix". (Transitions to `APPENDIX_PARSE`).
*   **4. Insufficient Evidence**: Any `is_outlier` that does not match "Appendix" (e.g., a bolded journal name).
*   **5. Same State**: All non-transitioning blocks create a `REFERENCES` leaf node.

---

## 2. Benchmark Replay

### Spanner
*   **Target Block**: "Google, Inc." (Distinct font size)
*   **Current State**: `FRONT_MATTER_PARSE`
*   **Evidence**: `is_outlier == True` (Does not start with "Abstract")
*   **Wrong Transition**: `BODY_PARSE` (Because any non-abstract outlier forced an exit)
*   **Correct Transition**: **None**. Stay in `FRONT_MATTER_PARSE` (Emit: `AUTHORS` / `AFFILIATION`).

### Attention Is All You Need
*   **Target Block**: "Jakob Uszkoreit & Illia Polosukhin" (Bold font)
*   **Current State**: `FRONT_MATTER_PARSE`
*   **Evidence**: `is_outlier == True`
*   **Wrong Transition**: `BODY_PARSE`
*   **Correct Transition**: **None**. Stay in `FRONT_MATTER_PARSE` (Emit: `AUTHORS`).

### BERT
*   **Target Block**: "Google AI Language" (Distinct font size)
*   **Current State**: `FRONT_MATTER_PARSE`
*   **Evidence**: `is_outlier == True`
*   **Wrong Transition**: `BODY_PARSE`
*   **Correct Transition**: **None**. Stay in `FRONT_MATTER_PARSE` (Emit: `AUTHORS`).

---

## 3. Rewriting PIP-003 Using the Transition Table

**Does PIP-003 become simpler after defining this transition table?**
**Yes.** The entire issue collapses into a single malformed edge in the state machine matrix. We do not need to reason about heuristics or architecture; we simply redefine the illegal edge.

**PIP-003 Refactored (State Machine Proof):**

**Original Illegal Edge (The Bug):**
$T(\text{FRONT\_MATTER}, \text{OUTLIER} \land \neg \text{"abstract"}) \rightarrow \text{BODY\_PARSE}$

**Corrected Edges (The Fix):**
1.  $T(\text{FRONT\_MATTER}, \text{OUTLIER} \land \text{"abstract"}) \rightarrow \text{FRONT\_MATTER} \quad [\text{Emit: ABSTRACT}]$
2.  $T(\text{FRONT\_MATTER}, \text{OUTLIER} \land (Stack\_Has\_Abstract \lor Valid\_Body\_Regex)) \rightarrow \text{BODY\_PARSE} \quad [\text{Emit: SECTION\_HEADER}]$
3.  $T(\text{FRONT\_MATTER}, \text{OUTLIER} \land \neg (Stack\_Has\_Abstract \lor Valid\_Body\_Regex)) \rightarrow \text{FRONT\_MATTER} \quad [\text{Emit: AUTHORS}]$
