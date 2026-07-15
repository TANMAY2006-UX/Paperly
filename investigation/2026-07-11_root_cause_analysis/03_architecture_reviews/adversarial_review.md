# Adversarial Review of the Proposed OUTLIER Contract

## Context
**Candidate Contract**: `OUTLIER = (curr != prev && curr != next)`

## Task 1 — The Adversarial Document (False Positives)

Consider an academic document containing the following sentence within a standard body paragraph:
> "For details on the architecture, see Section **1. Introduction**, which explains the core components."

*   **Prev**: "For details on the architecture, see Section " (Class 8: Normal)
*   **Curr**: "**1. Introduction**" (Class 6: Bold)
*   **Next**: ", which explains the core components." (Class 8: Normal)

**Why the proposed contract fails:**
The proposal strictly evaluates `curr != prev` ($6 \neq 8$) and `curr != next` ($6 \neq 8$). Both are `True`. The Landmark stage incorrectly flags this inline phrase as an `OUTLIER`. 
When Semantic Reconstruction receives this `OUTLIER`, it authorizes regex evaluation. The string `"1. Introduction"` perfectly matches the `SECTION_HEADER` lexical signature. Semantic will immediately fracture the paragraph and spawn a completely false Section AST node, permanently corrupting the document structure.

---

## Task 2 — Classification of Failures

| Failure Example | Classification | Reason |
| :--- | :--- | :--- |
| Inline bold phrase ("**1. Intro**") | **A** (Typography changed) | Purely stylistic emphasis on the same baseline; no structural shift. |
| Bold math equation ("**X = 1**") | **B** (Typography & Structure) | Forms a distinct mathematical block outside paragraph flow. |
| Footnote indicator ("^1") | **A** (Typography changed) | Superscript within text flow. |
| Table cell ("**1. Data**") | **B** (Typography & Structure) | Constrained within a grid layout, breaking linear flow. |
| Run-in Header ("**1. Intro.** We...") | **B** (Typography & Structure) | Initiates a new structural hierarchy at paragraph start. |

---

## Task 3 — Minimum Additional Invariant

To separate purely typographic changes (A) from structural changes (B) without using language or heuristics, we must rely on geometric flow.
The minimum additional invariant is **Geometric Baseline Isolation** (`y-axis` overlap).
An inline change (A) is completely encapsulated horizontally by surrounding text on the exact same baseline. A structural change (B) forms an isolated block or initiates a new vertical line.

---

## Task 4 — The Impossibility of a Stronger Deterministic Invariant

**Can spacing, alignment, baseline, font weight, etc., be combined into a stronger deterministic invariant?**
**No. It is mathematically impossible.**

**Proof:**
Consider two scenarios in documents with block-style paragraphs (flush left, no indents):
1.  **Scenario A (Run-in Header - Type B)**: Paragraph 1 ends. Paragraph 2 begins on a new line with "**1. Introduction.** The..."
2.  **Scenario B (Line-starting Inline Bold - Type A)**: Paragraph 1 contains a sentence that naturally wraps to a new line. The first word on the new line is "**1. Introduction**". 

In both scenarios:
*   $C_{curr} \neq C_{prev}$ (Bold vs Normal)
*   $x$-position is identical (flush left margin).
*   $y$-position breaks the baseline of the previous block (starts on a new line).
*   Line count is identical (1 line).

The only geometric difference is the vertical gap ($\Delta y$). Scenario A uses paragraph spacing ($\Delta y_{para}$); Scenario B uses line spacing ($\Delta y_{line}$). 
Because the compiler is deterministic and publisher-agnostic, it possesses no prior knowledge of what constitutes $\Delta y_{para}$ versus $\Delta y_{line}$ for an arbitrary PDF. Without injecting non-deterministic heuristic thresholds or relying on lexical NLP to read the text, the geometric and typographic vectors for these two blocks are mathematically identical.
Therefore, A and B cannot be perfectly separated.

---

## Task 5 — Replay Using the Bounded Invariant

Since perfect separation is impossible, we replay the strongest partial invariant we can derive logically (rejecting strictly encapsulated inline text):
$I = (C_{curr} \neq C_{prev} \land C_{curr} \neq C_{next}) \land \neg \text{SameBaseline}(prev, curr, next)$

*   **Spanner ("1. INTRODUCTION")**: Isolated block. Invariant HOLDS. `OUTLIER = True`.
*   **Attention ("Abstract")**: Isolated block. Invariant HOLDS. `OUTLIER = True`.
*   **BERT ("1 Introduction")**: Isolated block. Invariant HOLDS. `OUTLIER = True`.

**Adversarial Examples:**
1.  *Strictly Inline Bold*: Encapsulated on same baseline. Invariant REJECTS.
2.  *Footnote (isolated at bottom)*: Isolated block. Invariant HOLDS.
3.  *Caption*: Isolated block. Invariant HOLDS.
4.  *Equation*: Isolated block. Invariant HOLDS.
5.  *Line-starting Inline Bold ("**1. Introduction**")*: Escapes baseline encapsulation. Invariant HOLDS. $\leftarrow$ **Critical Failure**.

The invariant successfully processes standard academic layouts but still emits false positives on edge-case inline emphasis (Line-starting bold). When passed to Semantic, this false positive creates a phantom AST section.

---

## Task 6 — Final Verdict

**REJECT.**

The proposed contract (`curr != prev && curr != next`) fails. 
Because a deterministic compiler cannot mathematically separate an inline style change from a run-in structural header without relying on language or probabilistic heuristics, the proposal guarantees that false positives will leak into the Semantic stage. When adversarial typography collides with header regex signatures, it decisively breaks the AST. 

The proposal is fundamentally unsafe and cannot become a permanent compiler contract.
