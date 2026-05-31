from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from beatsync.dataset import index_ballroom, parse_beats_file, _split_of
from beatsync.eval import f_measure


def run_method(method: str, wav: str, device: str, checkpoint: str | None):
    if method == "librosa":
        from beatsync.dsp import detect_beats_librosa
        return detect_beats_librosa(wav).beats
    if method == "beat_this":
        from beatsync.ml import detect_beats_beat_this
        return detect_beats_beat_this(wav, device=device).beats
    if method == "tcn":
        from beatsync.tcn_infer import detect_beats_tcn
        return detect_beats_tcn(wav, checkpoint=checkpoint, device=device).beats
    raise ValueError(method)


def main():
    p = argparse.ArgumentParser(description="Benchmark beat trackers on the Ballroom val split")
    p.add_argument("--data", required=True, type=Path)
    p.add_argument("--methods", nargs="+", default=["librosa", "tcn", "beat_this"])
    p.add_argument("--val-fraction", type=float, default=0.15)
    p.add_argument("--limit", type=int, default=0, help="0 = all val files")
    p.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
    p.add_argument("--checkpoint", default=None)
    p.add_argument("--out", type=Path, default=Path("benchmark_report.md"))
    args = p.parse_args()

    pairs = [pp for pp in index_ballroom(args.data)
             if _split_of(pp[0].stem, args.val_fraction) == "val"]
    if args.limit:
        pairs = pairs[: args.limit]
    print(f"evaluating on {len(pairs)} val clips")

    results: dict = {}
    for method in args.methods:
        fs, t0 = [], time.time()
        for wav, beats_path in pairs:
            try:
                pred = run_method(method, str(wav), args.device, args.checkpoint)
                ref, _ = parse_beats_file(beats_path)
                fs.append(f_measure(pred, ref)["f_measure"])
            except Exception as e:
                print(f"  [{method}] {wav.name}: {e}")
        elapsed = time.time() - t0
        results[method] = {
            "f_mean": float(np.mean(fs)) if fs else 0.0,
            "f_std": float(np.std(fs)) if fs else 0.0,
            "n": len(fs),
            "sec_per_clip": elapsed / max(len(fs), 1),
        }
        print(f"{method:>10}: F={results[method]['f_mean']:.4f} "
              f"±{results[method]['f_std']:.3f}  "
              f"({results[method]['sec_per_clip']:.2f}s/clip)")

    lines = ["# BeatSync benchmark (Ballroom val)", "",
             f"Clips: {len(pairs)}", "",
             "| Method | F-measure | Std | Sec/clip |",
             "|---|---|---|---|"]
    for m, r in results.items():
        lines.append(f"| {m} | {r['f_mean']:.4f} | {r['f_std']:.3f} | {r['sec_per_clip']:.2f} |")
    args.out.write_text("\n".join(lines) + "\n")
    (args.out.with_suffix(".json")).write_text(json.dumps(results, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
