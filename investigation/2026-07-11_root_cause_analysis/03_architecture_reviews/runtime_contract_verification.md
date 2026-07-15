# Runtime Contract Verification
*Execution trace overriding previous static assumptions*

## Task 1 — Source Implementation Evidence

**1. Assignment (`extractor/preprocess.py`)**
```python
        def cluster_key(c):
            avg_size = sum(s[0] for s in c) / len(c)
            bold_val = c[0][1]
            return (avg_size, bold_val)
            
        all_clusters.sort(key=cluster_key)
                    
        # Assign sequential classes
        sig_to_class = {}
        for class_id, cluster in enumerate(all_clusters):
            for sig in cluster:
                sig_to_class[sig] = class_id
```

**2. Interpretation (`extractor/landmarks.py`)**
```python
        curr_emp = groups[i].typography_class
        
        prev_emp = groups[i-1].typography_class if i > 0 else -1
        next_emp = groups[i+1].typography_class if i < len(groups) - 1 else -1
        
        if curr_emp > prev_emp and curr_emp > next_emp:
            tokens.append(LandmarkToken(kind=LandmarkKind.OUTLIER, group_id=groups[i].group_id))
```

**3. Comparison (`extractor/semantic.py`)**
```python
                        # Using mathematical magnitude: smaller typography_class ID means physically larger text
                        if header_group and group.typography_class > header_group.typography_class:
                            break # New header is smaller structurally (larger class id), push as nested child
```

---

## Task 2 — Spanner Runtime State

```text
--------------------------------
Text (first 40 chars):
Spanner: Google's Globally Distributed D
Raw font size:
11.955100059509277
Bold:
True
typography_class:
9
is_anchor:
True
is_outlier:
True
--------------------------------
Text (first 40 chars):
JAMES C. CORBETT, JEFFREY DEAN, MICHAEL 
Raw font size:
9.962599754333496
Bold:
False
typography_class:
8
is_anchor:
False
is_outlier:
False
--------------------------------
Text (first 40 chars):
Spanner is Google's scalable, multiversi
Raw font size:
7.970099925994873
Bold:
False
typography_class:
3
is_anchor:
False
is_outlier:
False
--------------------------------
Text (first 40 chars):
1. INTRODUCTION
Raw font size:
8.966400146484375
Bold:
True
typography_class:
6
is_anchor:
False
is_outlier:
False
--------------------------------
Text (first 40 chars):
These features are enabled by the fact t
Raw font size:
9.962599754333496
Bold:
False
typography_class:
8
is_anchor:
False
is_outlier:
False
--------------------------------
Text (first 40 chars):
2. IMPLEMENTATION
Raw font size:
8.966400146484375
Bold:
True
typography_class:
6
is_anchor:
False
is_outlier:
False
--------------------------------
Text (first 40 chars):
We first measure Spanner's performance w
Raw font size:
9.962599754333496
Bold:
False
typography_class:
8
is_anchor:
False
is_outlier:
True
```

---

## Task 3 — Exact Landmark Equation

```python
        curr_emp = groups[i].typography_class
        
        prev_emp = groups[i-1].typography_class if i > 0 else -1
        next_emp = groups[i+1].typography_class if i < len(groups) - 1 else -1
        
        if curr_emp > prev_emp and curr_emp > next_emp:
```

---

## Task 4 — Replay Landmark Detection

For `"1. INTRODUCTION"`:

*   **prev value** (Abstract): 3
*   **current value** (1. INTRODUCTION): 6
*   **next value** (Body Paragraph): 8

**Comparison**:
*   `6 > 3` = `True`
*   `6 > 8` = `False`

**Therefore**: `OUTLIER = False`

---

## Task 5 — Architectural Conclusion

**B. No. The earlier analysis was incorrect.**

The architecture is mathematically consistent in mapping physical magnitudes. `preprocess.py` correctly assigns a *larger* `typography_class` to *larger* fonts (Title = 9, Body = 8). `landmarks.py` correctly seeks mathematical maxima by using the `>` operator. 

The previous contradiction theory relied on the *assumption* (influenced by a factually incorrect comment in `semantic.py`) that headers are physically larger than body text. 

The runtime data proves that the Spanner header font (8.96pt) is **physically smaller** than the Spanner body text (9.96pt). Because the header is a physical valley (6) surrounded by a physical peak (8), it is correctly rejected by the mathematical peak-finding equation in `landmarks.py`.
