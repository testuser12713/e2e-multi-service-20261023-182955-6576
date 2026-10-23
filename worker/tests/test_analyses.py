"""Tests for the pure analysis functions."""

from __future__ import annotations

import json

import pytest
from analyses import reading_time, run_analysis, top_words, word_count


def test_word_count_whitespace_tokens() -> None:
    assert word_count("eins zwei drei") == 3
    assert word_count("  eins\n zwei\tdrei  ") == 3
    assert word_count("") == 0


def test_top_words_ties_alphabetical_and_max_five() -> None:
    text = "f e d c b a a b"
    assert top_words(text) == [("a", 2), ("b", 2), ("c", 1), ("d", 1), ("e", 1)]


def test_top_words_case_and_punctuation() -> None:
    assert top_words("Hallo, hallo! HALLO. Welt?") == [("hallo", 3), ("welt", 1)]
    assert top_words("... !!") == []


def test_reading_time_boundaries() -> None:
    assert reading_time("") == 1
    assert reading_time(" ".join(["w"] * 200)) == 1
    assert reading_time(" ".join(["w"] * 201)) == 2


def test_run_analysis_formats() -> None:
    assert run_analysis("word_count", "eins zwei drei") == "3"
    assert run_analysis("reading_time", "eins") == "1"
    assert json.loads(run_analysis("top_words", "b a a")) == [
        {"word": "a", "count": 2},
        {"word": "b", "count": 1},
    ]


def test_run_analysis_unknown_raises_without_text() -> None:
    with pytest.raises(ValueError, match="Unknown analysis") as info:
        run_analysis("nope", "geheimer Text")
    assert "geheimer" not in str(info.value)
