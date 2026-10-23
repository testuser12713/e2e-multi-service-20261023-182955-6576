"""Text analyses the worker runs on a job's text.

Each analysis is a pure function of the text. ``run_analysis`` maps the ``analysis``
value stored with a job to its function and renders the result in the string format
stored in ``jobs.result``:

- ``word_count``   -> the number of words as a string (``"3"``)
- ``top_words``    -> a JSON list of ``{"word": str, "count": int}``, at most 5 entries
- ``reading_time`` -> whole minutes as a string

Words are whitespace-separated tokens. For ``top_words`` each token is lowercased and
stripped of leading/trailing punctuation; tokens that are pure punctuation are ignored.
"""

from __future__ import annotations

import json
import math
import string
from collections import Counter

ANALYSIS_KINDS = ("word_count", "top_words", "reading_time")


def word_count(text: str) -> int:
    """Number of words in ``text``."""
    return len(text.split())


def top_words(text: str) -> list[tuple[str, int]]:
    """The five most frequent words (case-insensitive) with their counts, ties alphabetical."""
    punctuation = (
        string.punctuation + "\u201e\u201c\u201d\u201a\u2018\u2019\u00ab\u00bb\u2026\u2013\u2014"
    )
    words = (token.strip(punctuation).lower() for token in text.split())
    counts = Counter(word for word in words if word)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]


def reading_time(text: str) -> int:
    """Reading time in whole minutes at 200 words per minute, rounded up, at least 1."""
    return max(1, math.ceil(word_count(text) / 200))


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
    raise ValueError("Unknown analysis")
