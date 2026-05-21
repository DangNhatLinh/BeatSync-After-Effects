"""Classical DSP baseline using librosa.

This is the no-ML path: STFT → onset-strength envelope → dynamic-programming beat
tracker (Ellis, 2007). Works on any machine, no GPU, no model checkpoint.
Performance is solid on steady 4/4 pop / EDM / hip-hop; weak on tempo changes,
swing, classical, and tracks with sparse percussion. That weakness is exactly
what the ML path in `ml.py` is meant to fix.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
import librosa
import numpy as np


@dataclass
class DspResult:
    tempo: float
    beats: np.ndarray       # beat times in seconds
    downbeats: np.ndarray   # estimated downbeats in seconds (heuristic for librosa)
    onsets: np.ndarray      # generic onsets in seconds

    def as_dict(self) -> dict:
        return {
            "tempo": float(self.tempo),
            "beats": self.beats.tolist(),
            "downbeats": self.downbeats.tolist(),
            "onsets": self.onsets.tolist(),
        }


def detect_beats_librosa(
    audio_path: str,
    sr: int = 22050,
    hop_length: int = 512,
    start_bpm: float = 120.0,
    tightness: float = 100.0,
) -> DspResult:
    """Run the librosa baseline on an audio file.

    Parameters
    ----------
    audio_path : str
        Path to a wav/mp3/flac/etc file (librosa handles most via soundfile/audioread).
    sr : int
        Resample rate. 22050 is the librosa convention and is plenty for beat tracking.
    hop_length : int
        STFT hop. 512 @ 22050 Hz → ~23 ms frames, the librosa default.
    start_bpm : float
        Tempo prior for the DP. 120 is reasonable for pop/EDM; lower for ballads.
    tightness : float
        How strictly the DP enforces the global tempo. Higher = more regular.

    Notes
    -----
    Downbeats are estimated by simply taking every 4th beat (assumes 4/4). This is a
    crude heuristic; the ML model in `ml.py` predicts downbeats directly.
    """
    y, sr = librosa.load(audio_path, sr=sr, mono=True)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    tempo, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_env,
        sr=sr,
        hop_length=hop_length,
        start_bpm=start_bpm,
        tightness=tightness,
        units="frames",
    )
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)

    # Crude downbeat heuristic: every 4th beat. Good enough for 4/4, garbage otherwise.
    downbeat_times = beat_times[::4] if len(beat_times) else beat_times

    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, hop_length=hop_length
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)

    tempo_scalar = float(np.atleast_1d(tempo).ravel()[0])

    return DspResult(
        tempo=tempo_scalar,
        beats=beat_times,
        downbeats=downbeat_times,
        onsets=onset_times,
    )


def estimate_tempo_from_beats(beats: List[float] | np.ndarray) -> float:
    """Median-IBI tempo estimate; useful when a beat tracker returns beats but no tempo."""
    beats = np.asarray(beats, dtype=float)
    if beats.size < 2:
        return 0.0
    ibis = np.diff(beats)
    median_ibi = float(np.median(ibis))
    if median_ibi <= 0:
        return 0.0
    return 60.0 / median_ibi
