from __future__ import annotations

import argparse
import json
from pathlib import Path


def pick_device(requested: str):
    import torch

    if requested != "auto":
        return requested
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def estimate_pos_weight(ds, n: int = 20) -> float:
    import numpy as np

    fracs = []
    for i in range(min(n, len(ds))):
        _, beat_t, _ = ds[i]
        arr = beat_t.numpy()
        fracs.append(float((arr > 0.05).mean()))
    frac = max(float(np.mean(fracs)), 1e-3)
    return float(min(max((1 - frac) / frac, 1.0), 50.0))


def validate(model, val_ds, device, cfg, threshold: float):
    import numpy as np
    import torch

    from .dataset import parse_beats_file
    from .eval import f_measure
    from .model import peak_pick_beats

    model.eval()
    fs = []
    with torch.no_grad():
        for i in range(len(val_ds)):
            mel, _, _ = val_ds[i]
            mel = mel.unsqueeze(0).to(device)
            out = model(mel)
            probs = torch.sigmoid(out["beat_logits"]).squeeze(0).cpu().numpy()
            pred = peak_pick_beats(probs, fps=cfg.fps, threshold=threshold)
            ref, _ = parse_beats_file(val_ds.pairs[i][1])
            fs.append(f_measure(pred, ref)["f_measure"])
    return float(np.mean(fs)) if fs else 0.0


def main():
    p = argparse.ArgumentParser(description="Train the BeatSync TCN")
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--lr", type=float, default=2e-3)
    p.add_argument("--segment-frames", type=int, default=500)
    p.add_argument("--val-fraction", type=float, default=0.15)
    p.add_argument("--threshold", type=float, default=0.4)
    p.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda", "mps"])
    args = p.parse_args()

    try:
        import torch
        from torch.utils.data import DataLoader
        from tqdm import tqdm
    except ImportError:
        raise SystemExit("pip install torch torchaudio tqdm mir_eval")

    from .dataset import BallroomDataset
    from .features import DEFAULT_MEL
    from .model import build_tcn

    cfg = DEFAULT_MEL
    device = pick_device(args.device)
    print(f"device: {device}")

    train_ds = BallroomDataset(args.data, split="train", val_fraction=args.val_fraction,
                               segment_frames=args.segment_frames, cfg=cfg)
    val_ds = BallroomDataset(args.data, split="val", val_fraction=args.val_fraction,
                             segment_frames=None, cfg=cfg)
    print(f"train clips: {len(train_ds)}   val clips: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=args.batch, shuffle=True, drop_last=True)

    model = build_tcn(n_mels=cfg.n_mels).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"model params: {n_params/1e3:.0f}k")

    pos_weight = estimate_pos_weight(train_ds)
    print(f"pos_weight: {pos_weight:.1f}")
    bce = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight, device=device))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)

    args.out.mkdir(parents=True, exist_ok=True)
    best_f = -1.0

    for epoch in range(args.epochs):
        model.train()
        running = 0.0
        for mel, beat_t, down_t in tqdm(train_loader, desc=f"epoch {epoch+1}/{args.epochs}"):
            mel = mel.to(device)
            beat_t = beat_t.to(device)
            down_t = down_t.to(device)
            out = model(mel)
            loss = bce(out["beat_logits"], beat_t)
            if "downbeat_logits" in out:
                loss = loss + bce(out["downbeat_logits"], down_t)
            opt.zero_grad()
            loss.backward()
            opt.step()
            running += loss.item()
        sched.step()

        val_f = validate(model, val_ds, device, cfg, args.threshold)
        avg = running / max(len(train_loader), 1)
        print(f"  loss {avg:.4f}   val F-measure {val_f:.4f}")

        if val_f > best_f:
            best_f = val_f
            ckpt = {
                "state_dict": model.state_dict(),
                "model_cfg": {"n_mels": cfg.n_mels},
                "mel_cfg": cfg.__dict__,
                "val_f_measure": val_f,
                "epoch": epoch,
            }
            torch.save(ckpt, args.out / "best.pt")
            (args.out / "best.json").write_text(json.dumps(
                {"val_f_measure": val_f, "epoch": epoch, "params": n_params}, indent=2))
            print(f"  saved best (F={val_f:.4f}) -> {args.out / 'best.pt'}")

    print(f"done. best val F-measure: {best_f:.4f}")


if __name__ == "__main__":
    main()
