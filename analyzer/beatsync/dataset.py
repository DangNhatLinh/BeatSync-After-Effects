from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Tuple

import numpy as np

from .features import DEFAULT_MEL, MelConfig, log_mel_spectrogram, load_audio
from .model import beats_to_target


def parse_beats_file(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    beats, downbeats = [], []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        t = float(parts[0])
        beats.append(t)
        if len(parts) > 1 and int(float(parts[1])) == 1:
            downbeats.append(t)
    return np.asarray(beats, dtype=float), np.asarray(downbeats, dtype=float)


def _split_of(name: str, val_fraction: float) -> str:
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    return "val" if (h % 1000) / 1000.0 < val_fraction else "train"


def index_ballroom(root: Path) -> List[Tuple[Path, Path]]:
    audio_dir = root / "ballroom" / "audio"
    annot_dir = root / "ballroom" / "annotations"
    pairs = []
    for wav in audio_dir.rglob("*.wav"):
        beats = annot_dir / (wav.stem + ".beats")
        if beats.exists():
            pairs.append((wav, beats))
    return sorted(pairs)


class BallroomDataset:
    """Yields (mel, beat_target, downbeat_target) for the custom TCN.

    Training mode crops a random fixed-length window; eval mode returns full clips.
    """

    def __init__(
        self,
        root: Path,
        split: str = "train",
        val_fraction: float = 0.15,
        segment_frames: int | None = 500,
        cfg: MelConfig = DEFAULT_MEL,
        cache: bool = True,
    ):
        import torch  # noqa: F401  (ensures torch present when dataset is used)

        self.cfg = cfg
        self.segment_frames = segment_frames
        self.split = split
        self._cache_enabled = cache
        self._cache: dict = {}

        all_pairs = index_ballroom(Path(root))
        if not all_pairs:
            raise FileNotFoundError(
                f"No (wav, .beats) pairs under {root}/ballroom. "
                "Run scripts/download_datasets.py first."
            )
        self.pairs = [p for p in all_pairs if _split_of(p[0].stem, val_fraction) == split]

    def __len__(self) -> int:
        return len(self.pairs)

    def _compute(self, idx: int):
        if self._cache_enabled and idx in self._cache:
            return self._cache[idx]
        wav, beats_path = self.pairs[idx]
        y = load_audio(str(wav), self.cfg)
        mel = log_mel_spectrogram(y, self.cfg)            # (n_mels, T)
        T = mel.shape[1]
        beats, downbeats = parse_beats_file(beats_path)
        beat_t = beats_to_target(beats, T, fps=self.cfg.fps)
        down_t = beats_to_target(downbeats, T, fps=self.cfg.fps)
        item = (mel, beat_t, down_t)
        if self._cache_enabled:
            self._cache[idx] = item
        return item

    def __getitem__(self, idx: int):
        import torch

        mel, beat_t, down_t = self._compute(idx)
        T = mel.shape[1]

        if self.segment_frames is not None and self.split == "train":
            S = self.segment_frames
            if T >= S:
                start = np.random.randint(0, T - S + 1)
                mel = mel[:, start:start + S]
                beat_t = beat_t[start:start + S]
                down_t = down_t[start:start + S]
            else:
                pad = S - T
                mel = np.pad(mel, ((0, 0), (0, pad)))
                beat_t = np.pad(beat_t, (0, pad))
                down_t = np.pad(down_t, (0, pad))

        return (
            torch.from_numpy(np.ascontiguousarray(mel)),
            torch.from_numpy(np.ascontiguousarray(beat_t)),
            torch.from_numpy(np.ascontiguousarray(down_t)),
        )
