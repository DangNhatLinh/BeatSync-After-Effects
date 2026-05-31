from __future__ import annotations


def build_tcn(
    n_mels: int = 81,
    hidden: int = 64,
    num_blocks: int = 8,
    kernel_size: int = 5,
    dropout: float = 0.1,
    predict_downbeats: bool = True,
):
    import torch
    from torch import nn

    class TcnBlock(nn.Module):
        def __init__(self, channels: int, ks: int, dilation: int, p: float):
            super().__init__()
            pad = (ks - 1) * dilation // 2
            self.conv = nn.Conv1d(channels, channels, ks, padding=pad, dilation=dilation)
            self.act = nn.GELU()
            self.drop = nn.Dropout(p)
            self.norm = nn.BatchNorm1d(channels)

        def forward(self, x):
            y = self.conv(x)
            y = self.norm(y)
            y = self.act(y)
            y = self.drop(y)
            return x + y

    class BeatTcn(nn.Module):
        def __init__(self):
            super().__init__()
            self.stem = nn.Sequential(
                nn.Conv2d(1, 16, kernel_size=(3, 3), padding=(1, 1)),
                nn.GELU(),
                nn.Conv2d(16, hidden, kernel_size=(n_mels, 1)),
                nn.GELU(),
            )
            self.blocks = nn.ModuleList(
                [TcnBlock(hidden, kernel_size, dilation=2**i, p=dropout) for i in range(num_blocks)]
            )
            self.beat_head = nn.Conv1d(hidden, 1, kernel_size=1)
            self.downbeat_head = (
                nn.Conv1d(hidden, 1, kernel_size=1) if predict_downbeats else None
            )

        def forward(self, mel):
            x = mel.unsqueeze(1)
            x = self.stem(x)
            x = x.squeeze(2)
            for block in self.blocks:
                x = block(x)
            beat_logits = self.beat_head(x).squeeze(1)
            out = {"beat_logits": beat_logits}
            if self.downbeat_head is not None:
                out["downbeat_logits"] = self.downbeat_head(x).squeeze(1)
            return out

    return BeatTcn()


def peak_pick_beats(
    probs,
    fps: float = 50.0,
    threshold: float = 0.4,
    min_distance_ms: int = 100,
):
    import numpy as np

    probs = np.asarray(probs).astype(float)
    if probs.ndim != 1:
        raise ValueError(f"expected 1D probs, got shape {probs.shape}")

    min_dist_frames = max(1, int(round(min_distance_ms * 1e-3 * fps)))
    candidates = []
    for i in range(len(probs)):
        if probs[i] < threshold:
            continue
        lo = max(0, i - min_dist_frames)
        hi = min(len(probs), i + min_dist_frames + 1)
        if probs[i] >= probs[lo:hi].max() - 1e-9:
            candidates.append(i)

    picked = []
    last = -10**9
    for i in candidates:
        if i - last >= min_dist_frames:
            picked.append(i)
            last = i
    return np.array(picked, dtype=float) / fps


def beats_to_target(beat_times, num_frames: int, fps: float = 50.0, sigma_frames: float = 2.0):
    import numpy as np

    target = np.zeros(num_frames, dtype="float32")
    if len(beat_times) == 0:
        return target

    beat_frames = np.round(np.asarray(beat_times) * fps).astype(int)
    beat_frames = beat_frames[(beat_frames >= 0) & (beat_frames < num_frames)]

    radius = int(np.ceil(3 * sigma_frames))
    kernel_x = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (kernel_x / sigma_frames) ** 2)

    for f in beat_frames:
        lo = max(0, f - radius)
        hi = min(num_frames, f + radius + 1)
        k_lo = lo - (f - radius)
        k_hi = k_lo + (hi - lo)
        target[lo:hi] = np.maximum(target[lo:hi], kernel[k_lo:k_hi])

    return target
