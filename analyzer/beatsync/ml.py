"""Neural beat-tracking path.

We wrap the *Beat This!* model (CPJKU, ISMIR 2024) as the pretrained ML option.
Install with:

    pip install https://github.com/CPJKU/beat_this/archive/main.zip

The import is deferred so the rest of the analyzer keeps working on machines that
only have the librosa baseline installed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .dsp import estimate_tempo_from_beats


@dataclass
class MlResult:
    tempo: float
    beats: np.ndarray
    downbeats: np.ndarray
    onsets: np.ndarray   # not predicted by Beat This!; left empty for schema parity

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
    """Run the Beat This! pretrained model.

    Parameters
    ----------
    audio_path : str
        Path to the audio file. WAV is safest; for mp3/flac, ffmpeg must be on PATH.
    checkpoint : str
        Pretrained checkpoint name. "final0" is the default released checkpoint;
        "final1"/"final2" are the same model with different training seeds (use the
        ensemble of all three for a small accuracy bump).
    device : str
        "cpu" or "cuda". CPU is fine for offline analysis (≈ realtime or faster).
    use_dbn : bool
        Whether to postprocess with a DBN. Off by default — the whole point of
        Beat This! is that it doesn't need one and generalizes better without.
    """
    try:
        from beat_this.inference import File2Beats  # type: ignore
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
