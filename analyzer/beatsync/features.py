from __future__ import annotations

from dataclasses import dataclass

import librosa
import numpy as np


@dataclass(frozen=True)
class MelConfig:
    sr: int = 22050
    n_fft: int = 2048
    hop_length: int = 441
    n_mels: int = 81
    fmin: float = 30.0
    fmax: float = 11000.0

    @property
    def fps(self) -> float:
        return self.sr / self.hop_length


DEFAULT_MEL = MelConfig()


def load_audio(audio_path: str, cfg: MelConfig = DEFAULT_MEL) -> np.ndarray:
    y, _ = librosa.load(audio_path, sr=cfg.sr, mono=True)
    return y


def log_mel_spectrogram(y: np.ndarray, cfg: MelConfig = DEFAULT_MEL) -> np.ndarray:
    mel = librosa.feature.melspectrogram(
        y=y,
        sr=cfg.sr,
        n_fft=cfg.n_fft,
        hop_length=cfg.hop_length,
        n_mels=cfg.n_mels,
        fmin=cfg.fmin,
        fmax=cfg.fmax,
        power=1.0,
    )
    log_mel = np.log1p(mel).astype("float32")
    mean = log_mel.mean()
    std = log_mel.std() + 1e-6
    return (log_mel - mean) / std


def mel_from_file(audio_path: str, cfg: MelConfig = DEFAULT_MEL) -> np.ndarray:
    return log_mel_spectrogram(load_audio(audio_path, cfg), cfg)
