from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .dsp import estimate_tempo_from_beats


@dataclass
class MlResult:
    tempo: float
    beats: np.ndarray
    downbeats: np.ndarray
    onsets: np.ndarray

    def as_dict(self) -> dict:
        return {
            "tempo": float(self.tempo),
            "beats": self.beats.tolist(),
            "downbeats": self.downbeats.tolist(),
            "onsets": self.onsets.tolist(),
        }


def detect_beats_beat_this(
    audio_path: str,
    checkpoint: str = "final0",
    device: str = "cpu",
    use_dbn: bool = False,
) -> MlResult:
    try:
        from beat_this.inference import File2Beats
    except ImportError as e:
        raise ImportError(
            "beat_this is not installed.\n"
            "Install with:\n"
            "  pip install https://github.com/CPJKU/beat_this/archive/main.zip"
        ) from e

    f2b = File2Beats(checkpoint_path=checkpoint, device=device, dbn=use_dbn)
    beats, downbeats = f2b(audio_path)

    beats = np.asarray(beats, dtype=float)
    downbeats = np.asarray(downbeats, dtype=float)

    return MlResult(
        tempo=estimate_tempo_from_beats(beats),
        beats=beats,
        downbeats=downbeats,
        onsets=np.array([], dtype=float),
    )
