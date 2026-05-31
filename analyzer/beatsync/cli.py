from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import infer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="beatsync", description="BeatSync analyzer")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_infer = sub.add_parser("infer")
    p_infer.add_argument("--audio", required=True, type=Path)
    p_infer.add_argument("--out", required=True, type=Path)
    p_infer.add_argument("--method", choices=["librosa", "beat_this", "tcn"], default="librosa")
    p_infer.add_argument("--device", default="cpu", choices=["cpu", "cuda", "mps"])
    p_infer.add_argument("--checkpoint", default=None, help="Path to a trained TCN checkpoint")
    p_infer.add_argument("--quiet", action="store_true")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.cmd == "infer":
        if not args.audio.exists():
            print(f"audio file not found: {args.audio}", file=sys.stderr)
            return 2
        payload = infer.analyze(args.audio, method=args.method, device=args.device,
                                checkpoint=args.checkpoint)
        infer.write_json(payload, args.out)
        if not args.quiet:
            print(
                f"wrote {args.out}  "
                f"({len(payload['beats'])} beats, "
                f"tempo ≈ {payload['tempo']:.1f} BPM, "
                f"method={args.method})"
            )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
