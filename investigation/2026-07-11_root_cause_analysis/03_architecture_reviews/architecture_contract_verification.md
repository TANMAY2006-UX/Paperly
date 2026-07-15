# Architecture Contract Verification
*Strict Lifecycle and Consistency Audit*

## Task 1 — Lifecycle of `typography_class`

1. **PyMuPDF**
   *   Extracts physical font size (float) and weight (boolean) from the raw PDF binary.
2. **Assembly (`preprocess.py`)**
   *   Clusters raw blocks by identical size and weight.
   *   Assigns a sequential integer (`typography_class`) to each cluster. 
   *   Based on the user's observation (`class = 1` for a header) and downstream documentation, the sorting is inverted: **Smaller integer = Larger physical font** (e.g., Title=0, Header=1, Body=2).
3. **Quantization**
   *   (Logic is merged into Assembly). The `typography_class` becomes the immutable representation of visual magnitude.
4. **Landmarks (`landmarks.py`)**
   *   Compares the integer values to find structural transitions.
   *   Assumes: **Larger integer = Larger physical font**. (It searches for mathematical maxima using `>`).
   *   *Inversion occurs here*: It treats the integer as directly proportional to size, breaking the inverse relationship established in Assembly.
5. **Semantic (`semantic.py`)**
   *   Consumes the groups and landmarks to build the AST.
   *   Assumes: **Smaller integer = Larger physical font**. (Explicitly documented in line 160).

---

## Task 2 — Source Code Comparisons

| File | Function | Line | Comparison | Purpose | Assumed Mapping |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `landmarks.py` | `detect_landmarks` | 28 | `emp > max_emphasis` | Identify Title (ANCHOR) | **Larger ID == Larger Font** |
| `landmarks.py` | `detect_landmarks` | 40 | `curr_emp > prev_emp` | Identify Headers (OUTLIER) | **Larger ID == Larger Font** |
| `semantic.py` | `reconstruct_semantics` | 141 | `group.class == body.class`| Identify standard text | Neutral (Equality check) |
| `semantic.py` | `reconstruct_semantics` | 156 | `group.class > header.class`| Resolve AST nesting depth | **Smaller ID == Larger Font** |

*(Note: In semantic.py, `group.class > header.class` triggers a `break` to ascend the hierarchy because the new header is physically smaller, meaning its class ID is mathematically larger).*

---

## Task 3 — Module Agreement Matrix

| Module | Assumption | Evidence | Compatible |
| :--- | :--- | :--- | :--- |
| `preprocess.py` | **Smaller ID = Larger Font** | Assigns `class=1` to Spanner headers | **YES** (Schema Owner) |
| `semantic.py` | **Smaller ID = Larger Font** | Inline comment (Line 160) | **YES** |
| `landmarks.py`| **Larger ID = Larger Font** | Uses `>` to find emphasis peaks | **NO** (Contradiction) |

---

## Task 4 — Contradiction Origin

The EARLIEST module introducing the contradiction is **`landmarks.py`**.

It expects `typography_class` to scale directly with physical size, while the rest of the architecture explicitly defines it as an inversely scaling rank. 

---

## Task 5 — Pipeline Replay ("1. INTRODUCTION")

1.  **Assembly**
    *   *Input*: Raw blocks for abstract, "1. INTRODUCTION", and body text.
    *   *Decision*: Header is physically larger than body text. Assigns smaller integer to larger text. (Header = 1, Body = 2).
    *   *Output*: `TypographicGroup(text="1. INTRODUCTION", typography_class=1)`.
2.  **Landmarks**
    *   *Input*: The ordered group sequence.
    *   *Decision*: Evaluates `curr_emp > prev_emp` ($1 > 2$). This evaluates to `False`.
    *   *Output*: **`is_outlier = False`** $\leftarrow$ **FIRST INCORRECT DETERMINISTIC DECISION**.
3.  **Semantic**
    *   *Input*: Group with `is_outlier = False`.
    *   *Decision*: Evaluates `if is_outlier:` (False). Drops into the default `else` branch.
    *   *Output*: Creates `AUTHORS` node.

---

## Task 6 — Mathematical Proof of Algorithm Failure

**Theorem**: Under the established architectural schema, a physical heading can never become an `OUTLIER`.

**Proof**:
1. By schema contract (Assembly & Semantic), physical emphasis $P$ is inversely proportional to the class integer $C$. Thus, $P_x > P_y \iff C_x < C_y$.
2. Let $H$ be a heading block surrounded sequentially by normal text blocks $B_{prev}$ and $B_{next}$.
3. By physical definition, a heading possesses greater emphasis than standard text: $P_H > P_{prev}$ and $P_H > P_{next}$.
4. Substituting the inverse schema mapping: $C_H < C_{prev}$ and $C_H < C_{next}$.
5. The `landmarks.py` algorithm enforces the condition: $C_H > C_{prev} \land C_H > C_{next}$.
6. Therefore, for a heading to become an `OUTLIER`, its class integer $C_H$ must be simultaneously strictly less than and strictly greater than the surrounding body integers.
7. This is a mathematical impossibility.

**Conclusion**: The Landmark algorithm structurally rejects all physical maxima. The algorithm itself is mathematically incorrect and must be inverted to comply with the architecture.
