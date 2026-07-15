# 2026-07-11 Root Cause Analysis

This directory contains the complete, frozen investigation package into the compiler's structural extraction failures (specifically the PIP-003 Spanner header omission bug).

## Directory Structure

*   **`01_pips/`**: Problem Investigation Plans and root cause proofs (e.g., PIP-003).
*   **`02_experiments/`**: Controlled telemetry, candidate set measurements, separability analyses, and behavior experiment designs (EXP-01 through EXP-11).
*   **`03_architecture_reviews/`**: Deep-dive audits into the compiler's interfaces, runtime contracts, and verification pipelines.
*   **`04_adrs/`**: Architectural Decision Records defining ownership and rejecting dangerous or coupled refactoring proposals.
*   **`05_implementation_specs/`**: Precise, behavior-preserving refactoring plans and impact analyses designed to safely decouple multiplexed code.
*   **`06_outputs/`**: Reserved for raw JSON extractions and benchmark outputs.
*   **`07_visual_outputs/`**: Reserved for debug visualizations and telemetry charts.
*   **`08_summary/`**: Executive summary of the investigation timeline, hypotheses, and current status.
