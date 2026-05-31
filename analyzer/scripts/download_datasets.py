from __future__ import annotations

import argparse
import io
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

BALLROOM_AUDIO_URL = "http://mtg.upf.edu/ismir2004/contest/tempoContest/data1.tar.gz"
BALLROOM_ANNOT_URL = "https://github.com/CPJKU/BallroomAnnotations/archive/refs/heads/master.zip"


def _download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  already downloaded: {dest.name}")
        return dest
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "beatsync/0.1"})
    with urllib.request.urlopen(req) as r, dest.open("wb") as f:
        total = int(r.headers.get("Content-Length", 0))
        read = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            read += len(chunk)
            if total:
                pct = 100 * read / total
                sys.stdout.write(f"\r  {read >> 20} / {total >> 20} MB ({pct:.0f}%)")
                sys.stdout.flush()
        sys.stdout.write("\n")
    return dest


def download_ballroom(root: Path) -> None:
    base = root / "ballroom"
    audio_dir = base / "audio"
    annot_dir = base / "annotations"

    print("Ballroom: audio")
    tar_path = _download(BALLROOM_AUDIO_URL, base / "data1.tar.gz")
    if not audio_dir.exists():
        print("  extracting audio…")
        audio_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path, "r:gz") as t:
            t.extractall(audio_dir)
    n_wav = len(list(audio_dir.rglob("*.wav")))
    print(f"  {n_wav} wav files")

    print("Ballroom: annotations")
    if not annot_dir.exists():
        annot_dir.mkdir(parents=True, exist_ok=True)
        print("  downloading annotations…")
        req = urllib.request.Request(BALLROOM_ANNOT_URL, headers={"User-Agent": "beatsync/0.1"})
        with urllib.request.urlopen(req) as r:
            data = r.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                if name.endswith(".beats"):
                    target = annot_dir / Path(name).name
                    with z.open(name) as src, target.open("wb") as dst:
                        dst.write(src.read())
    n_beats = len(list(annot_dir.glob("*.beats")))
    print(f"  {n_beats} annotation files")

    if n_wav == 0:
        print(
            "\nWARNING: no audio extracted. The MTG mirror is sometimes down.\n"
            "Manually place .wav files under:\n"
            f"  {audio_dir}\n"
            "and re-run with --skip-audio.",
            file=sys.stderr,
        )


def main():
    p = argparse.ArgumentParser(description="Download beat-tracking datasets")
    p.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "datasets" / "raw",
        help="Where datasets land (default: <repo>/datasets/raw)",
    )
    p.add_argument("--dataset", choices=["ballroom"], default="ballroom")
    args = p.parse_args()

    args.root.mkdir(parents=True, exist_ok=True)
    if args.dataset == "ballroom":
        download_ballroom(args.root)
    print("done.")


if __name__ == "__main__":
    main()
