"""Training loop for the custom TCN beat tracker.

This is intentionally a scaffold — the real work in M3 is implementing the dataset
loader for Ballroom / Hainsworth / GTZAN-Rhythm. Each of those ships annotations as
plain text files (one beat-time-in-seconds per line, with an integer indicating
beat position-in-bar for downbeats), so the loader is mostly a `glob` + `np.loadtxt`.

Run:

    python -m beatsync.train --data datasets/raw --out analyzer/checkpoints
"""

from __future__ import annotations

import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True, type=Path, help="Root of dataset folder")
    p.add_argument("--out", required=True, type=Path, help="Checkpoint output dir")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
    args = p.parse_args()

    try:
        import torch
    except ImportError:
        raise SystemExit(
            "torch is required for training. Install with:\n"
            "  pip install torch torchaudio tqdm mir_eval"
        )

    from .model import build_tcn

    args.out.mkdir(parents=True, exist_ok=True)

    # TODO(M3): implement BeatDataset that yields (log_mel: (n_mels, T),
    # beat_target: (T,), downbeat_target: (T,)). See model.beats_to_target.
    raise NotImplementedError(
        "Dataset loader is the M3 task. See PROJECT_PLAN.md § Datasets and\n"
        "model.beats_to_target() for the label format."
    )

    # Sketch of what comes next, kept here as a guide:
    #
    # net = build_tcn().to(args.device)
    # opt = torch.optim.AdamW(net.parameters(), lr=args.lr)
    # bce = torch.nn.BCEWithLogitsLoss()
    # for epoch in range(args.epochs):
    #     for mel, beat_y, db_y in loader:
    #         out = net(mel.to(args.device))
    #         loss = bce(out["beat_logits"], beat_y.to(args.device))
    #         if "downbeat_logits" in out:
    #             loss = loss + bce(out["downbeat_logits"], db_y.to(args.device))
    #         opt.zero_grad(); loss.backward(); opt.step()
    #     torch.save(net.state_dict(), args.out / f"epoch_{epoch:03d}.pt")


if __name__ == "__main__":
    main()
