# BeatSync — Project Plan

The goal of this document is to keep the project from sprawling. Every milestone below
should leave the repo in a working, demoable state.

---

## North star

> Select an audio layer in After Effects, click one button, get clean beat markers on
> the timeline. Optionally choose between *every beat* / *downbeats only* / *kick-only* /
> *bar-level cuts*, all driven by a trained model that beats `librosa` on hard songs.

---

## Milestones

### M1 — End-to-end skeleton (DONE on scaffold)

- [x] `analyzer/beatsync/dsp.py` produces a working `beats.json` from any audio file via `librosa`.
- [x] `extension/jsx/BeatSync.jsx` reads `beats.json` and places markers on the selected AE layer.
- [x] CLI entry point: `python -m beatsync.cli infer ...`.

**Demo at the end of M1**: analyze a 4/4 pop track → drop the JSON into AE → markers appear on every beat. This alone is already useful.

### M2 — Neural beat tracker (pretrained)

- [ ] Wire `Beat This!` (CPJKU, ISMIR 2024) as `--method beat_this` in `infer.py`.
- [ ] Add `--downbeats` flag so the panel can place "bar markers" instead of "beat markers".
- [ ] Side-by-side comparison notebook: `librosa` vs `Beat This!` on 5 hard songs (tempo changes, swing, classical, hip-hop with sparse drums, lo-fi).
- [ ] Show that the neural model wins on the hard cases.

**Why this matters**: this is the cheapest way to get "ML inside the project" without training anything. It also gives you the benchmark scaffolding you'll reuse in M3.

### M3 — Train your own model (the "impressive" part)

- [ ] Download Ballroom + Hainsworth + GTZAN-Rhythm via `analyzer/scripts/download_datasets.py`.
- [ ] Implement target generation: convert annotated beat times → per-frame Gaussian targets at the mel-spec frame rate (see `model.py` docstring).
- [ ] Train a small **Temporal Convolutional Network (TCN)** on mel spectrograms in `train.py`.
  - Input: log-mel spectrogram, 81 mel bands, 22.05 kHz, hop=441 (≈ 50 fps).
  - Output: per-frame beat probability (+ optional downbeat head).
  - Loss: BCE with a ±2-frame tolerance on the target Gaussians.
- [ ] Evaluate with F-measure / CMLt / AMLt in `eval.py` against `librosa` and `Beat This!` on a held-out set (e.g. SMC, GTZAN — *never* train on these).
- [ ] Produce a results table for the README.

**Stretch**: replace TCN with a small conv+transformer block, à la *Beat This!* but ~10× fewer parameters, and report the trade-off.

### M4 — CEP panel ("real plugin")

- [ ] `extension/panel/CSXS/manifest.xml` registers the panel for AE 2024+.
- [ ] Panel UI: pick audio (or auto-detect from selected layer), method dropdown (`librosa` / `beat_this` / `tcn`), checkboxes (beats / downbeats / onsets), "Analyze & Place" button.
- [ ] Panel spawns the Python analyzer via `window.cep.process`, waits for `beats.json`, then calls `host.jsx` to place markers.
- [ ] Sign the bundle with `ZXPSignCmd`, ship a `BeatSync.zxp` in releases.

### M5 — Editor-grade features

- [ ] Marker colors / labels: `beat`, `downbeat`, `drop`, `kick`.
- [ ] "Quantize selected keyframes to nearest beat" button.
- [ ] "Generate cut markers every N bars" button (super useful for music videos).
- [ ] Section detection (intro/verse/chorus/drop) using a small CNN on chromagram — colors the markers by section.

---

## Datasets

Annotated beat-tracking datasets, all standard in the literature:

| Dataset | Tracks | Genre | License | Notes |
| --- | --- | --- | --- | --- |
| Ballroom | 698 | Dance (8 styles) | Research-only | Easy 4/4, strong beats. Good first training set. |
| Hainsworth | 222 | Mixed | Research-only | Harder, varied. |
| GTZAN-Rhythm | 999 | 10 genres | Research-only | Reuses GTZAN audio with added beat annotations. |
| SMC Mirum | 217 | Mixed/hard | Research-only | Held-out / test only — known to be brutal. |
| GiantSteps Tempo | 664 | Electronic | CC | Tempo-only, useful for tempo head pretraining. |

Put download URLs in `analyzer/scripts/download_datasets.py` (TODO in M3).
`datasets/raw/` is gitignored — never commit audio.

---

## Out of scope (for now)

- Real-time beat tracking inside AE during playback (would need BeatNet + a different IPC story).
- Mobile / Premiere Pro / DaVinci Resolve ports. The CEP host JSX is reusable across Adobe apps but each host has its own marker API.
- Beat-driven motion generation (auto wiggle / auto opacity pulse). Could be a follow-up project.
