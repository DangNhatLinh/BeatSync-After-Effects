"""Schema for the beats.json payload consumed by the After Effects extension.

Keep this file dependency-free so the JSX bridge in the CEP panel can mirror it.
"""

from __future__ import annotations

from typing import Iterable, Optional

SCHEMA_VERSION = 1


def make_payload(
    *,
    source: str,
    method: str,
    tempo: float,
    beats: Iterable[float],
    downbeats: Optional[Iterable[float]] = None,
    onsets: Optional[Iterable[float]] = None,
    extra: Optional[dict] = None,
) -> dict:
    """Build the canonical beats.json payload."""
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source": str(source),
        "method": method,
        "tempo": float(tempo),
        "beats": [float(t) for t in beats],
        "downbeats": [float(t) for t in (downbeats or [])],
        "onsets": [float(t) for t in (onsets or [])],
    }
    if extra:
        payload["extra"] = extra
    return payload
