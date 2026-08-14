"""Deterministic context packing and optional compressor contracts.

The default packer is lossless: it selects whole segments and never rewrites
their bytes.  A compressor is an explicit plugin.  Lossy output is rejected
unless the host provides a reversible result and a recovery handle (durable
CCR belongs in the Tokenisme gateway or another host integration).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

from . import estimate


@dataclass(frozen=True)
class ContextSegment:
    id: str
    text: str
    kind: str = "text"
    priority: int = 0
    relevance: float = 0.0
    recency: float = 0.0
    error: bool = False
    security: bool = False
    stable: bool = False
    provenance: str = ""


@dataclass(frozen=True)
class CompressionResult:
    text: str
    method: str
    lossless: bool
    reversible: bool = False
    recovery_handle: str | None = None
    original_sha256: str = ""
    reason: str = ""


@dataclass(frozen=True)
class PackedContext:
    text: str
    segments: tuple[ContextSegment, ...]
    dropped: tuple[ContextSegment, ...]
    estimated_tokens: int
    budget_tokens: int | None
    basis: str
    compression: tuple[dict, ...] = ()


class Compressor(Protocol):
    name: str

    def compress(self, segment: ContextSegment) -> CompressionResult:
        ...


_COMPRESSORS: dict[str, Compressor] = {}


def register_compressor(compressor: Compressor) -> None:
    name = str(getattr(compressor, "name", "")).strip()
    if not name:
        raise ValueError("compressor needs a name")
    _COMPRESSORS[name] = compressor


def clear_compressors() -> None:
    _COMPRESSORS.clear()


def _tokens(text: str, model: str | None) -> tuple[int, str]:
    return estimate.count_for_model(text, model=model)


def _original_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _safe_transform(
    segment: ContextSegment,
    *,
    compressor: str | Compressor | None,
    allow_lossy: bool,
) -> tuple[ContextSegment, dict]:
    """Apply one plugin with fail-closed validation."""
    if compressor is None:
        return segment, {"method": "identity", "accepted": True, "lossless": True}
    plugin = _COMPRESSORS.get(compressor) if isinstance(compressor, str) else compressor
    if plugin is None:
        return segment, {"method": "identity", "accepted": False, "reason": "unknown_compressor"}
    original = segment.text
    try:
        result = plugin.compress(segment)
    except Exception as exc:  # plugin errors never remove original context
        return segment, {"method": getattr(plugin, "name", "plugin"), "accepted": False,
                         "reason": f"plugin_error:{type(exc).__name__}"}
    if not isinstance(result, CompressionResult):
        return segment, {"method": getattr(plugin, "name", "plugin"), "accepted": False,
                         "reason": "invalid_result"}
    expected_hash = _original_hash(original)
    if result.original_sha256 and result.original_sha256 != expected_hash:
        return segment, {"method": result.method, "accepted": False, "reason": "hash_mismatch"}
    if not result.text or len(result.text.encode("utf-8")) >= len(original.encode("utf-8")):
        return segment, {"method": result.method, "accepted": False, "reason": "not_smaller"}
    if not result.lossless and not allow_lossy:
        return segment, {"method": result.method, "accepted": False, "reason": "lossy_disabled"}
    if not result.lossless and (not result.reversible or not result.recovery_handle):
        return segment, {"method": result.method, "accepted": False,
                         "reason": "lossy_requires_reversible_recovery"}
    transformed = ContextSegment(
        id=segment.id,
        text=result.text,
        kind=segment.kind,
        priority=segment.priority,
        relevance=segment.relevance,
        recency=segment.recency,
        error=segment.error,
        security=segment.security,
        stable=segment.stable,
        provenance=segment.provenance,
    )
    return transformed, {
        "method": result.method,
        "accepted": True,
        "lossless": result.lossless,
        "reversible": result.reversible,
        "recovery_handle": result.recovery_handle,
        "original_sha256": expected_hash,
    }


def pack_segments(
    segments: Iterable[ContextSegment],
    *,
    budget_tokens: int | None = None,
    model: str | None = None,
    compressor: str | Compressor | None = None,
    allow_lossy: bool = False,
    separator: str = "\n\n",
) -> PackedContext:
    """Pack whole segments by safety/relevance/recency in stable order.

    Security/error segments are pinned first.  Remaining segments are sorted
    deterministically and admitted while the token budget permits.  If pinned
    segments alone exceed the budget they remain present and the result marks
    ``budget_exceeded``; silently deleting safety context is never allowed.
    """
    original = list(segments)
    indexed = list(enumerate(original))
    indexed.sort(key=lambda pair: (
        0 if (pair[1].security or pair[1].error) else 1,
        -int(pair[1].priority),
        -float(pair[1].relevance),
        -float(pair[1].recency),
        pair[0],
    ))
    chosen: list[ContextSegment] = []
    dropped: list[ContextSegment] = []
    compression_meta: list[dict] = []
    total = 0
    for _, segment in indexed:
        candidate, meta = _safe_transform(
            segment, compressor=compressor, allow_lossy=allow_lossy)
        n, method = _tokens(candidate.text, model)
        pinned = segment.security or segment.error
        if budget_tokens is not None and chosen and total + n > max(0, budget_tokens) and not pinned:
            dropped.append(segment)
            meta = {**meta, "id": segment.id, "accepted": False, "reason": "budget"}
            compression_meta.append(meta)
            continue
        chosen.append(candidate)
        total += n
        compression_meta.append({**meta, "id": segment.id, "tokens": n, "token_method": method})
    text = separator.join(segment.text for segment in chosen)
    basis = "inferred" if any(_tokens(s.text, model)[1] == "~est" for s in chosen) else "tokenizer"
    if budget_tokens is not None and total > max(0, budget_tokens):
        basis += ";budget_exceeded_by_pinned_context"
    return PackedContext(
        text=text,
        segments=tuple(chosen),
        dropped=tuple(dropped),
        estimated_tokens=total,
        budget_tokens=budget_tokens,
        basis=basis,
        compression=tuple(compression_meta),
    )


class FunctionCompressor:
    """Small convenience adapter for hosts that prefer a function."""

    def __init__(self, name: str, function: Callable[[ContextSegment], CompressionResult]):
        self.name = name
        self._function = function

    def compress(self, segment: ContextSegment) -> CompressionResult:
        return self._function(segment)
