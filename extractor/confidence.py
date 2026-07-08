# Phase 3A.1 Semantic Classifiers Confidence Thresholds

# Base thresholds (strong evidence required)
TITLE_THRESHOLD = 0.85
AUTHOR_THRESHOLD = 0.70
HEADER_THRESHOLD = 0.75
REFERENCE_THRESHOLD = 0.80

# Fallback thresholds (weak evidence, used when nothing else matches)
TITLE_FALLBACK_THRESHOLD = 0.30

# Additional thresholds
AFFILIATION_THRESHOLD = 0.65
ABSTRACT_THRESHOLD = 0.80
KEYWORD_THRESHOLD = 0.80
EQUATION_THRESHOLD = 0.75
FIGURE_CAPTION_THRESHOLD = 0.85
TABLE_CAPTION_THRESHOLD = 0.85
NOISE_THRESHOLD = 0.90

# Penalty factors (applied to base confidence when anomalies detected)
NON_STANDARD_FONT_PENALTY = 0.15
POOR_POSITION_PENALTY = 0.20
