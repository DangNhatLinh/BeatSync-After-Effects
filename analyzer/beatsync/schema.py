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
    payload = {
        "schema_version": SCHEMA_VERSION,
        "source": str(source),
        "method": method,
        "tempo": float(tempo),
        "beats": [float(t) for t in beats],
        "downbeats": [float(t) for t in (downbeats if downbeats is not None else [])],
        "onsets": [float(t) for t in (onsets if onsets is not None else [])],
    }
    if extra:
        payload["extra"] = extra
    return payload
