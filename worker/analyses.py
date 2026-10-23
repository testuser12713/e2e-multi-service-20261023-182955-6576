"""Text analyses the worker runs on a job's text.

Each analysis is a pure function of the text. ``run_analysis`` maps the ``analysis``
value stored with a job to its function and renders the result in the string format
stored in ``jobs.result``:

- ``word_count``   -> the number of words as a string (``"3"``)
- ``top_words``    -> a JSON list of ``{"word": str, "count": int}``, at most 5 entries
- ``reading_time`` -> whole minutes as a string

The three analysis bodies are skeleton placeholders returning an empty result; the
ticket "Implement the pure analysis functions" fills them in.
"""

from __future__ import annotations

import json

ANALYSIS_KINDS = ("word_count", "top_words", "reading_time")


def word_count(text: str) -> int:
    """Number of words in ``text``."""
    return 0


def top_words(text: str) -> list[tuple[str, int]]:
    """The five most frequent words (case-insensitive) with their counts, ties alphabetical."""
    return []


def reading_time(text: str) -> int:
    """Reading time in whole minutes at 200 words per minute, rounded up, at least 1."""
    return 0


def run_analysis(analysis: str, text: str) -> str:
    """Run the analysis named ``analysis`` on ``text`` and return the stored result string.

    Raises ``ValueError`` for an analysis name that is not one of ``ANALYSIS_KINDS``.
    The message never quotes the text.
    """
    if analysis == "word_count":
        return str(word_count(text))
    if analysis == "top_words":
        return json.dumps(
            [{"word": word, "count": count} for word, count in top_words(text)],
            ensure_ascii=False,
        )
    if analysis == "reading_time":
        return str(reading_time(text))
    raise ValueError(f"unknown analysis {analysis[:40]!r}")
