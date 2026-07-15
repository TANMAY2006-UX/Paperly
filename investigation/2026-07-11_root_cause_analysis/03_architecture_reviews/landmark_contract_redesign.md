# Landmark Contract Redesign
*Evidence-First Compiler Research Review*

## Task 1 — The Purpose of Landmark
The mathematical purpose of the Landmark stage is to flag points of typographic discontinuity within the geometric sequence of blocks, serving as uninterpreted structural boundaries for Semantic Reconstruction.

---

## Task 2 — Failures of "Local Maximum" (Runtime Evidence)

**1. Spanner: "1. INTRODUCTION"**
*   **Why it is formatted this way**: Publisher constraints likely required tighter column packing, resulting in a slightly smaller font size (8.96pt vs 9.96pt body) but increased weight (Bold) to retain emphasis.
*   **Perceived structural information**: A distinct regime break signaling a new semantic section.
*   **Why Local Maximum fails**: It evaluates the 1D scalar equivalent of size. Because $8.96 < 9.96$, the header forms a mathematical *valley* rather than a peak, rendering it invisible to a maxima detector.

**2. Attention Is All You Need: "Abstract"**
*   **Why it is formatted this way**: Often styled as bold but smaller or identical in size to body text to differentiate it from main section headers.
*   **Perceived structural information**: Separation of front matter from the document body.
*   **Why Local Maximum fails**: Being smaller or equal to surrounding text guarantees it will fail a strict scalar `<` or `>` test intended for finding mathematical "peaks".

**3. BERT: "1 Introduction"**
*   **Why it is formatted this way**: Sized slightly larger (11.95pt) than body (10.90pt) and bolded.
*   **Perceived structural information**: Start of the main document body.
*   **Why Local Maximum fails**: While it is a peak relative to the body, if the preceding author/abstract blocks are also large ($\geq 11.95pt$), it fails the strict strict $C_{curr} > C_{prev}$ inequality.

---

## Task 3 — Geometric and Typographic Invariants

Without relying on language, regex, or probabilities, the following invariants remain:
1.  **Font Size Transition** ($\Delta$ Size)
2.  **Font Weight Transition** ($\Delta$ Weight)
3.  **Vertical Gap / Leading Space** ($\Delta$ Y)
4.  **Horizontal Alignment** (Centering, Left/Right Justification)
5.  **Indentation** ($\Delta$ X)
6.  **Block Density** (Line Spacing)
7.  **Column Span** (Single vs Multi-column width)
8.  **Character Casing** (All-Caps proportion)

---

## Task 4 — Typographic Invariant Matrix

| Invariant | TITLE | SECTION | BODY | AUTHOR | CAPTION | REFERENCE | TABLE/FIG |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Size $\Delta$** | Maximum | Changed | Neutral | Changed | Smaller | Smaller | N/A |
| **Weight $\Delta$** | Bold | Bold | Normal | Normal | Mixed | Normal | N/A |
| **Vertical Gap** | Huge | Large | Small | Medium | Medium | Small | Large |
| **Alignment** | Centered | Left/Center | Justified | Centered | Centered | Left | N/A |
| **Indentation** | None | None | First Line | None | None | Hanging | N/A |
| **Column Span**| Full Width| Bounded | Bounded | Full Width| Bounded | Bounded | Full/Bound|

---

## Task 5 — Ideal Landmark Token (Information Theory)

An ideal Landmark token should represent a **`VISUAL_BOUNDARY`** (or `STYLE_CHANGE`).

Based on information theory, Semantic Reconstruction does not need to know "this is the most important text" (a ranking). It only requires the minimal signal indicating that *the continuous stylistic regime has been broken*. Semantic reconstructs the hierarchy by analyzing the bounded regions between these breaks.

---

## Task 6 — Single Token Definition

If the Landmark stage could emit only ONE token type:
*   **Meaning**: `VISUAL_BOUNDARY` — The typographic continuity of the document has fractured at this exact block.
*   **Must Contain**: The geometric location (Group ID) and the delta transition vectors (e.g., changed to bold, decreased size, large vertical gap).
*   **Must NEVER Contain**: Semantic labels (e.g., "Header", "Abstract"), linguistic probabilities, or absolute hierarchy rankings (e.g., "Maximum", "Anchor").

---

## Task 7 — Document Simulation

Simulating the three benchmark papers, `VISUAL_BOUNDARY` tokens would be emitted exactly when the visual document changes:

1.  **Emitted before Title**: The visual document changed from empty space to a massive font.
2.  **Emitted before Authors**: The visual document changed (font size dropped, weight changed).
3.  **Emitted before Abstract**: The visual document changed (font size dropped again, entered column boundaries).
4.  **Emitted before "1. INTRODUCTION"**: The visual document changed (weight shifted from Normal to Bold, vertical gap appeared, size shifted).
5.  **Emitted before first Body Paragraph**: The visual document changed (weight returned to Normal, size returned to baseline).
6.  **Emitted before References**: The visual document changed (hanging indentation appeared, possible size drop).

In every case, the emission is triggered by a *delta* ($\Delta \neq 0$), not by achieving a global or local scalar maximum.

---

## Task 8 — Engineering Conclusion

**Should Landmark detect:**
**C) Visual boundaries**

**Runtime Evidence:**
In the Spanner paper, "1. INTRODUCTION" is 8.96pt and the body text is 9.96pt. Detecting "Visual maxima" completely misses this structural header because it is a mathematical minimum (valley). However, detecting a "Visual boundary" succeeds universally because a clear transition in font size ($9.96 \rightarrow 8.96$) and font weight ($False \rightarrow True$) unequivocally occurred. 

By signaling boundaries rather than enforcing a 1D scalar hierarchy, the Landmark stage provides Semantic with the exact structural breakpoints needed to parse any deterministic document format reliably.
