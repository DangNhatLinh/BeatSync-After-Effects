from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .dsp import estimate_tempo_from_beats
from .features import MelConfig, mel_from_file
from .model import build_tcn, peak_pick_beats


@dataclass
class TcnResult:
    tempo: float
    beats: np.ndarray
    downbeats: np.ndarray
    onsets: np.ndarray


def _default_checkpoint() -> Path:
    return Path(__file__).resolve().parents[1] / "checkpoints" / "best.pt"


def detect_beats_tcn(
    audio_path: str,
    checkpoint: str | None = None,
    device: str = "cpu",
    threshold: float = 0.4,
) -> TcnResult:
    import torch

    ckpt_path = Path(checkpoint) if checkpoint else _default_checkpoint()
    if not ckpt_path.exists():
        raise FileNotFoundError(
            f"No trained checkpoint at {ckpt_path}. Train one first:\n"
            "  python -m beatsync.train --data datasets/raw --out analyzer/checkpoints"
        )

    ckpt = torch.load(ckpt_path, map_location=device)
    cfg = MelConfig(**ckpt.get("mel_cfg", {}))
    model = build_tcn(**ckpt.get("model_cfg", {"n_mels": cfg.n_mels})).to(device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    mel = mel_from_file(audio_path, cfg)
    mel_t = torch.from_numpy(mel).unsqueeze(0).to(device)

    with torch.no_grad():
        out = model(mel_t)
        beat_probs = torch.sigmoid(out["beat_logits"]).squeeze(0).cpu().numpy()
        beats = peak_pick_beats(beat_probs, fps=cfg.fps, threshold=threshold)
        downbeats = np.array([], dtype=float)
        if "downbeat_logits" in out:
            db_probs = torch.sigmoid(out["downbeat_logits"]).squeeze(0).cpu().numpy()
            downbeats = peak_pick_beats(db_probs, fps=cfg.fps, threshold=threshold,
                                        min_distance_ms=300)

    return TcnResult(
        tempo=estimate_tempo_from_beats(beats),
        beats=beats,
        downbeats=downbeats,
        onsets=np.array([], dtype=float),
    )
