"""Gemini research wrapper — Google Search Grounding.

Mirrors Bull's src/research/gemini.py interface so usage is consistent.
Cloud routines clone fresh each run, so no on-disk cache (would be useless).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "gemini-2.5-flash"


@dataclass
class ResearchResult:
    answer: str
    citations: list[str]
    model: str


def _extract_citations(grounding_metadata) -> list[str]:
    citations: list[str] = []
    if grounding_metadata is None:
        return citations
    for chunk in getattr(grounding_metadata, "grounding_chunks", None) or []:
        web = getattr(chunk, "web", None)
        if web is not None:
            url = getattr(web, "uri", None)
            if url:
                citations.append(url)
    return citations


def research(
    prompt: str,
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    temperature: float = 0.2,
) -> ResearchResult:
    """Query Gemini Flash with Google Search Grounding for citation-backed research."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY env var not set")

    # Lazy import — keeps module importable without google-genai installed.
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=temperature,
        tools=[types.Tool(google_search=types.GoogleSearch())],
        system_instruction=system,
    )
    response = client.models.generate_content(model=model, contents=prompt, config=config)

    answer = response.text or ""
    grounding = None
    if response.candidates:
        grounding = getattr(response.candidates[0], "grounding_metadata", None)
    return ResearchResult(answer=answer, citations=_extract_citations(grounding), model=model)


def research_safe(prompt: str, **kwargs) -> ResearchResult:
    """Like research() but never raises — returns empty answer on failure. Use for non-critical paths."""
    try:
        return research(prompt, **kwargs)
    except Exception as exc:
        return ResearchResult(answer=f"[research error: {exc}]", citations=[], model=DEFAULT_MODEL)
