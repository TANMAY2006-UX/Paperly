# Paperly (Working Title)

## Background

This project originated during a one-week product-thinking exercise at Frappe.

Initially, I was building an LMS (Library Management System) with librarians, issue books, CRUD operations, admin panels, etc.

After several days, I realized that although technically educational, I was not emotionally invested in the problem.

During discussions with the CEO and CTO, three questions emerged:

1. Why will users come to your app?
2. Do you genuinely enjoy solving the problem?
3. Will somebody pay for or care about what you are building?

These questions led me to rethink the direction.

I realized that I genuinely enjoy reading research papers, understanding ideas, and making knowledge more accessible.

However, existing experiences are painful:

* Google Scholar focuses on discovery, not reading.
* arXiv looks archival rather than reader-friendly.
* PDFs are designed for printing, not digital consumption.
* Metadata, citations, and dense paragraphs create cognitive overload.
* Readers often get intimidated before understanding even begins.

The goal is NOT to simplify research.

The goal is to simplify the experience of approaching research.

---

# Core Philosophy

Research papers are already intellectually difficult.

They do not need to be visually difficult as well.

We are not changing the content.

We are changing the medium through which users consume it.

Our belief:

> Research papers should be consumed as a sequence of ideas, not as giant PDF documents.

---

# Product Statement

Read research, not PDFs.

OR

Research papers deserve a reading experience designed for humans.

OR

The internet stores research papers. We help humans comfortably read them.

---

# Problem Statement

Current problems:

* Massive walls of text.
* Tiny fonts.
* Two-column layouts.
* Metadata before content.
* Interruptive citations.
* Infinite scrolling.
* Poor typography.
* Difficult navigation.
* No concept-based progress tracking.
* PDF viewers introduce unnecessary distractions.

---

# Target Users

* Engineering students.
* Developers.
* Curious learners.
* Researchers exploring new domains.
* People reading papers for projects or understanding concepts.

---

# Key Insight

Books optimize for immersion.

Research papers optimize for understanding.

The application must therefore optimize for:

* Confidence.
* Navigation.
* Chunked reading.
* Reduced cognitive load.
* Better visual hierarchy.

---

# Scope (One Week)

This is NOT:

* Google Scholar.
* ResearchGate.
* Semantic Scholar.
* AI paper summarizer.
* Chat with PDFs.
* Recommendation engine.

This IS:

A better reading experience for a curated collection of research papers.

---

# Initial Dataset

Approximately 40–50 open-access papers.

Categories:

* Artificial Intelligence
* Computer Networks
* Databases
* Systems
* HCI
* Design
* Web Engineering

Only 5–10 papers need complete transformation into the new reading experience.

---

# Architecture

Pipeline:

PDF
↓
Gemini Flash
↓
Structured JSON
↓
Flask Rendering Engine

No AI runs inside the application.

Gemini is only a preprocessing tool.

---

# JSON Structure

{
"title": "...",
"authors": [],
"abstract": "...",
"keywords": [],
"sections": [
{
"title": "...",
"content": "...",
"estimated_reading_time": 3
}
],
"figures": [
{
"caption": "..."
}
]
}

---

# Reader Modes

## 1. Focus Mode (Default)

One section at a time.

Abstract
↓
Introduction
↓
Background
↓
Methodology
↓
Results
↓
Conclusion

The user never feels overwhelmed.

---

## 2. Scroll Mode

Traditional continuous reading.

Similar to Medium.

---

## 3. Scholar Mode

Everything visible:

* References
* Metadata
* Figures
* Citations

---

# Design Philosophy

Inspired by editorial reading systems.

References:

* Kindle
* Medium
* Notion
* Obsidian Reader

Avoid:

* Glassmorphism
* Fancy gradients
* Excessive cards
* Overwhelming sidebars

Design should disappear while reading.

---

# Homepage

Minimal.

Search:

"Search papers or topics..."

Categories:

* Artificial Intelligence
* Systems
* Networks
* Databases
* HCI

---

# Paper Detail Page

Show:

* Title
* Authors
* Abstract
* Estimated reading time
* Keywords
* Start Reading
* Download Original PDF

Avoid unnecessary metadata initially.

---

# Reader Features

Must Have:

* Adjustable typography
* Dark mode
* Highlights
* Reading progress
* Section navigation
* Focus mode
* Citation minimization
* Better paragraph spacing
* Comfortable line widths

---

# Typography

Defaults:

* Font Size: 18px
* Line Height: 1.8
* Maximum Width: 720px
* Serif fonts
* Generous whitespace

Whitespace is considered a feature.

---

# Important Principle

We do not ask users to read 35 pages.

We ask them to understand one idea at a time.
