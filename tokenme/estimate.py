"""Token estimation.

Two backends:
  1. tiktoken  - uses tiktoken (cl100k_base or o200k_base) if installed.
                 Labelled "tiktoken:<encoding>" — model-specific, NOT "exact",
                 because Claude and other providers use proprietary tokenizers
                 that are not identical to any public tiktoken encoding.
  2. heuristic - stdlib only. Transparent, documented. Labelled "~est".
                 Blends a chars/token and a token-piece count. Unvalidated
                 against a ground-truth corpus; treat as an order-of-magnitude
                 estimate, not a measurement.

count() returns (tokens, method) so every consumer can label or check precision.
is_estimate(method) -> True for anything not tiktoken-labelled.
"""
from __future__ import annotations

import re

_ENCODINGS: dict = {}   # cache: enc_name -> encoder object
_TRIED: set = set()

_CHARS_PER_TOKEN = 4.0
_WORD_RE = re.compile(r"\w+|[^\w\s]")

_O200K_TRIGGERS = ("gpt-4o", "o1-", "o3-", "o4-", "o1", "o3", "o4")


def _enc_for_model(model: str | None) -> str:
    """Best-effort encoding name for a model string."""
    if model:
        m = model.lower()
        if any(m.startswith(t) or t in m for t in _O200K_TRIGGERS):
            return "o200k_base"
    return "cl100k_base"


def _load(enc_name: str):
    if enc_name in _ENCODINGS:
        return _ENCODINGS[enc_name]
    if enc_name in _TRIED:
        return None
    _TRIED.add(enc_name)
    try:
        import tiktoken  # type: ignore
        _ENCODINGS[enc_name] = tiktoken.get_encoding(enc_name)
    except Exception:
        _ENCODINGS[enc_name] = None
    return _ENCODINGS[enc_name]


def heuristic_tokens(text: str) -> int:
    """Stdlib token estimate. Blends char-based and token-piece-based counts.
    No calibration data; accuracy is unverified — treat as approximate."""
    if not text:
        return 0
    char_est = len(text) / _CHARS_PER_TOKEN
    pieces = _WORD_RE.findall(text)
    piece_est = sum(1 + (len(p) - 1) // 6 for p in pieces)
    return max(1, round((char_est + piece_est) / 2))


def count(text: str | None, force_heuristic: bool = False) -> tuple[int, str]:
    """Return (tokens, method).
    method is '~est' or 'tiktoken:<enc>' — never bare 'exact'."""
    if text is None:
        return 0, "~est"
    if not force_heuristic:
        enc = _load("cl100k_base")
        if enc is not None:
            try:
                return len(enc.encode(text)), "tiktoken:cl100k_base"
            except Exception:
                pass
    return heuristic_tokens(text), "~est"


def count_for_model(
    text: str | None,
    model: str | None = None,
    force_heuristic: bool = False,
) -> tuple[int, str]:
    """Count tokens using the best-fit encoding for a named model.
    Falls back to heuristic if tiktoken is absent."""
    if text is None:
        return 0, "~est"
    if not force_heuristic:
        enc_name = _enc_for_model(model)
        enc = _load(enc_name)
        if enc is not None:
            try:
                return len(enc.encode(text)), f"tiktoken:{enc_name}"
            except Exception:
                pass
    return heuristic_tokens(text), "~est"


def count_n(text: str | None, force_heuristic: bool = False) -> int:
    return count(text, force_heuristic)[0]


def is_estimate(method: str | None) -> bool:
    """True if the method is a heuristic estimate rather than a tiktoken count."""
    if not method:
        return True
    return not method.startswith("tiktoken:")
