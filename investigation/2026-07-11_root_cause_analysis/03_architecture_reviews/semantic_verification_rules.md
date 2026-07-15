# Semantic Verification Rules
*Permanent Architecture Documentation*

This document defines the strict deterministic verification rules applied by Semantic Reconstruction (`semantic.py`) before assigning a semantic role to a text block. `OUTLIER` status indicates typographic emphasis but grants no structural authority until these proofs are satisfied.

## 1. ABSTRACT
| Attribute | Contract Rule |
| :--- | :--- |
| **Required evidence** | <ul><li>Parser state is `FRONT_MATTER_PARSE`.</li><li>Text begins with "Abstract" (case-insensitive).</li></ul> |
| **Optional evidence** | <ul><li>Tagged as an `OUTLIER`.</li><li>Isolated on its own line (short character length).</li></ul> |
| **Negative evidence** | <ul><li>Exceeds typical heading length without containing paragraph text.</li></ul> |
| **Decision order** | Evaluated 1st in `FRONT_MATTER_PARSE`. |
| **Fallback behaviour** | Evaluates as `SECTION_HEADER`, then `PARAGRAPH`. |

## 2. SECTION_HEADER
| Attribute | Contract Rule |
| :--- | :--- |
| **Required evidence** | <ul><li>Tagged as an `OUTLIER`.</li><li>Short text length (typically < 4 lines).</li></ul> |
| **Optional evidence** | <ul><li>Begins with section numbering (e.g., "1.", "I.", "A.").</li><li>Title-casing or all-caps.</li><li>Matches known structural keywords ("Introduction", "Background").</li></ul> |
| **Negative evidence** | <ul><li>Contains mostly numeric characters (e.g., table data, coordinates).</li><li>Ends with a terminal punctuation mark (period, question mark) indicating a full sentence.</li><li>Matches caption prefixes ("Figure", "Table").</li></ul> |
| **Decision order** | Evaluated 3rd in `BODY_PARSE` (after Reference Header and Caption). |
| **Fallback behaviour** | `PARAGRAPH` |

## 3. CAPTION
| Attribute | Contract Rule |
| :--- | :--- |
| **Required evidence** | <ul><li>Text exactly matches caption regex prefix (e.g., "Figure [X]", "Fig. [X]", "Table [X]") at the beginning of the block.</li></ul> |
| **Optional evidence** | <ul><li>Tagged as an `OUTLIER` (often bolded or smaller font).</li></ul> |
| **Negative evidence** | <ul><li>None (Prefix match is highly deterministic in academic text).</li></ul> |
| **Decision order** | Evaluated 2nd in `BODY_PARSE`. |
| **Fallback behaviour** | `PARAGRAPH` |

## 4. REFERENCE_HEADER
| Attribute | Contract Rule |
| :--- | :--- |
| **Required evidence** | <ul><li>Tagged as an `OUTLIER`.</li><li>Text strictly matches "References", "Bibliography", or "Literature Cited" (case-insensitive, optional numbering).</li></ul> |
| **Optional evidence** | <ul><li>Located in the final 20% of the document.</li></ul> |
| **Negative evidence** | <ul><li>Embedded within a longer sentence (e.g., "See the references below.").</li></ul> |
| **Decision order** | Evaluated 1st in `BODY_PARSE` and `REFERENCES_PARSE`. |
| **Fallback behaviour** | `SECTION_HEADER` |

## 5. AFFILIATION
| Attribute | Contract Rule |
| :--- | :--- |
| **Required evidence** | <ul><li>Parser state is `FRONT_MATTER_PARSE`.</li><li>Contains institutional or academic keywords ("University", "Institute", "Department", "Laboratories", "Inc.", "Research") OR contains an email indicator ("@").</li></ul> |
| **Optional evidence** | <ul><li>Tagged as an `OUTLIER`.</li></ul> |
| **Negative evidence** | <ul><li>Contains the word "Abstract".</li><li>Strictly comma-separated list of names with no institutional markers.</li></ul> |
| **Decision order** | Evaluated 2nd in `FRONT_MATTER_PARSE`. |
| **Fallback behaviour** | `AUTHORS` |

## 6. AUTHORS
| Attribute | Contract Rule |
| :--- | :--- |
| **Required evidence** | <ul><li>Parser state is `FRONT_MATTER_PARSE`.</li><li>Fails `AFFILIATION` keyword checks.</li></ul> |
| **Optional evidence** | <ul><li>Tagged as an `OUTLIER`.</li><li>Comma-separated or contains "and" / "&".</li></ul> |
| **Negative evidence** | <ul><li>Matches any section header prefix ("1.", "Abstract").</li><li>Exceeds standard author block length (indicating preamble noise).</li></ul> |
| **Decision order** | Evaluated 3rd in `FRONT_MATTER_PARSE`. |
| **Fallback behaviour** | `PARAGRAPH` (or pre-title `NOISE`) |

## 7. PARAGRAPH
| Attribute | Contract Rule |
| :--- | :--- |
| **Required evidence** | <ul><li>None. This is the terminal leaf node of the semantic evaluation chain.</li></ul> |
| **Optional evidence** | <ul><li>Typography class perfectly matches the `universal_body_class`.</li><li>Ends with a terminal punctuation mark.</li></ul> |
| **Negative evidence** | <ul><li>Satisfies the requirements of any higher-order structural node (`CAPTION`, `SECTION_HEADER`).</li></ul> |
| **Decision order** | Evaluated Last in all states. |
| **Fallback behaviour** | `NOISE` (if geometry/length indicates it is unreadable). |
