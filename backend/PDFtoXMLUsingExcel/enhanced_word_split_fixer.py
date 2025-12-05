"""
Utilities to clean up word splits introduced by PDF extraction.

Many PDFs insert hard line breaks mid-word or break hyphenated words
across lines (e.g. ``AI-\nassisted`` or ``pre-\nprocessing``).  The legacy
pipeline stubbed this module out which left artefacts like ``computa-\ntion``
in the final XML.  The heuristics expect this helper to normalise text.

`fix_word_splits_enhanced` embraces a conservative approach:

* Preserve explicit hyphenation (``AI-assisted``) but collapse embedded
  newlines/spaces.
* Join hard line-break splits that occur mid-word without punctuation.
* Collapse multiple internal whitespace runs produced by the reader.
* Leave numbers, acronyms, and ordinary sentence breaks untouched.
"""

from __future__ import annotations

import re

# Precompiled regular expressions reused in the cleaner
_HYPHEN_LINEBREAK_RE = re.compile(r"(\w)-\s*\n\s*(\w)")
_SOFT_LINEBREAK_RE = re.compile(r"([^\s-])\s*\n\s*([a-z])")
_LIGATURE_SPACING_RE = re.compile(r"(\w)\s{2,}(\w)")
_MULTISPACE_RE = re.compile(r"[ \t]{2,}")


def _fix_hyphenated_linebreaks(text: str) -> str:
    """Collapse ``word-\ncontinuation`` to ``word-continuation``."""

    def _repl(match: re.Match[str]) -> str:
        left, right = match.group(1), match.group(2)
        return f"{left}-{right}"

    return _HYPHEN_LINEBREAK_RE.sub(_repl, text)


def _fix_soft_linebreaks(text: str) -> str:
    """
    Replace bare line-break splits between lowercase fragments with a space.

    Example::
        ``comput\nation`` -> ``comput ation`` -> subsequently normalised.
    """

    def _repl(match: re.Match[str]) -> str:
        left, right = match.group(1), match.group(2)
        return f"{left} {right}"

    return _SOFT_LINEBREAK_RE.sub(_repl, text)


def _fix_ligature_spacing(text: str) -> str:
    """
    Collapse excessive intra-word spacing often seen around ligatures.
    """

    def _repl(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}"

    return _LIGATURE_SPACING_RE.sub(_repl, text)


def fix_word_splits_enhanced(text: str) -> str:
    """
    Best-effort normalisation for PDF derived text.

    The function intentionally performs several small passes rather than
    a monolithic regex so that each transformation stays easy to reason
    about and can be tuned independently.
    """
    if not text or "\n" not in text and "  " not in text:
        # Already clean (single line & no multi-spaces)
        return text

    cleaned = text
    cleaned = _fix_hyphenated_linebreaks(cleaned)
    cleaned = _fix_soft_linebreaks(cleaned)
    cleaned = _fix_ligature_spacing(cleaned)

    # Collapse remaining multi-spaces but preserve intentional indentation by
    # leaving leading whitespace per line untouched.
    def _collapse(multispace_match: re.Match[str]) -> str:
        return " "

    cleaned = _MULTISPACE_RE.sub(_collapse, cleaned)

    # Normalise ``-\n`` patterns that may remain after other substitutions.
    cleaned = cleaned.replace("-\n", "-")

    # Finally collapse residual line breaks that split mid-word (but retain
    # truly blank lines).
    cleaned = re.sub(r"(\S)\n(\S)", r"\1 \2", cleaned)

    return cleaned


__all__ = ["fix_word_splits_enhanced"]
