"""Audio → beats.json. Used by both the CLI and (via subprocess) the CEP panel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from . import schema

Method = Literal["librosa", "beat_this"]


def analyze(
    audio_path: str | Path,
    method: Method = "librosa",
    device: str = "cpu",
) -> dict:
    audio_path = str(audio_path)

    if method == "librosa":
        from . import dsp
        result = dsp.detect_beats_librosa(audio_path)
    elif method == "beat_this":
        from . import ml
        result = ml.detect_beats_beat_this(audio_path, device=device)
    else:
        raise ValueError(f"unknown method: {method!r}")

    return schema.make_payload(
        source=audio_path,
        method=method,
        tempo=result.tempo,
        beats=result.beats,
        downbeats=result.downbeats,
        onsets=result.onsets,
    )


def write_json(payload: dict, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return out_path
