#!/usr/bin/env python3
"""Offline quickstart for ppt-quality-review (Layer 1 — no API key needed).

Reviews a slide-deck DESCRIPTION (the structured dict your generator
produces before rendering) with the 4D quality framework and the
CJK-aware content-density analyzer.

Run:  python examples/heuristic_review.py
"""
from ppt_quality_review import analyze_content_density, analyze_quality_4d

# Slide descriptions as produced by a deck generator: one dict per slide.
SLIDES = [
    {"type": "title", "title": "Introduction to Vector Databases"},
    {"type": "outline", "title": "Overview", "items": ["What", "Why", "How"]},
    {
        "type": "content",
        "title": "What is a vector database?",
        "points": [
            "Stores embeddings instead of rows",
            "Similarity search via ANN indexes",
            "Powers retrieval-augmented generation",
        ],
    },
    {
        "type": "content",
        "title": "Why it matters",
        "points": ["Semantic recall", "Scale to billions of vectors"],
    },
    {"type": "summary", "title": "Takeaways", "items": ["Embeddings", "ANN", "RAG"]},
]


def main() -> None:
    report = analyze_quality_4d(SLIDES)
    print(report.summary())
    for issue in report.all_issues:
        print(f"  [{issue.severity}] {issue.dimension}/{issue.code}: {issue.message}")
    print(f"passing={report.is_passing}")

    density = analyze_content_density(SLIDES)
    print(
        f"\nDensity: {density.total_slides} slides "
        f"({density.content_slides} content), "
        f"score={density.overall_score:.2f}, "
        f"errors={len(density.errors)}, passing={density.is_passing}"
    )


if __name__ == "__main__":
    main()
