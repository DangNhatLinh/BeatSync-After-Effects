# BeatSync for After Effects

Automatically place timeline markers on every beat of an audio layer in After Effects, using a hybrid of classical DSP and modern deep-learning beat trackers.

```
[audio file]  →  Python analyzer  →  beats.json  →  AE extension  →  markers on the timeline
            (librosa | custom TCN | Beat This!)      (CEP panel or .jsx)
```

## Results

A custom 249k-parameter Temporal Convolutional Network, trained from scratch on the
Ballroom dataset, evaluated against a classical DSP baseline (librosa) and a published
state-of-the-art transformer (*Beat This!*, CPJKU, ISMIR 2024). Metric is F-measure
with a ±70 ms tolerance window on a held-out validation split.

| Method | F-measure | Std | Speed (sec/clip) | Params |
|---|---|---|---|---|
| librosa (classical DSP baseline) | 0.799 | 0.197 | 0.08 | — |
| **BeatSync TCN (this project)** | **0.952** | **0.056** | **0.08** | **249k** |
| Beat This! (SOTA transformer) | 0.988 | 0.015 | 0.91 | ~20M |

The trained TCN beats the classical baseline by **+15 F-measure points**, lands within
**~4 points of the state of the art**, and runs **~11× faster** than it at **~80× fewer
parameters**. Reproduce with `python scripts/benchmark.py --data ../datasets/raw`.

## Using it as a plugin in After Effects

1. Install the analyzer once (see below).
2. In AE, drop an audio file into a comp and select the audio layer.
3. `File > Scripts > Run Script File…` → `extension/jsx/BeatSync.jsx`.
4. In the dialog, pick a detection method (defaults to your trained model), choose
   beats / downbeats / onsets, and click **Analyze & place**.
5. Markers land on the selected layer.

> The script calls Python at the path in its `PYTHON_CANDIDATES` list (top of the file).
> Edit that if your environment differs. A CEP panel version also lives in
> `extension/panel/` for a dockable in-app UI.

## Install the analyzer

```bash
cd analyzer
pip install -r requirements.txt          # librosa baseline
pip install -r requirements-ml.txt       # torch + the trained-model path
```

Command-line use (optional — the AE script does this for you):

```bash
python -m beatsync.cli infer --audio path/to/song.wav --out beats.json                  # librosa
python -m beatsync.cli infer --audio path/to/song.wav --out beats.json --method tcn --device mps
```

## Training your own model

```bash
pip install -r requirements-ml.txt

# 1. Download the Ballroom dataset (~700 dance tracks + beat annotations)
python scripts/download_datasets.py

# 2. Train the TCN (uses Apple MPS / CUDA automatically)
python -m beatsync.train --data ../datasets/raw --out checkpoints --epochs 60

# 3. Benchmark librosa vs your TCN vs Beat This!
python scripts/benchmark.py --data ../datasets/raw --device mps
```

## Repo layout

```
analyzer/                   Python: DSP + ML pipeline
  beatsync/
    dsp.py                  librosa baseline
    ml.py                   Beat This! wrapper (pretrained SOTA)
    model.py                custom TCN architecture
    features.py             shared log-mel spectrogram (train + infer)
    dataset.py              Ballroom PyTorch dataset
    train.py                training loop (MPS/CUDA aware)
    tcn_infer.py            inference with a trained TCN checkpoint
    eval.py                 F-measure / CMLt / AMLt evaluation
    infer.py                audio → beats.json (librosa | tcn | beat_this)
    schema.py               beats.json schema
  cli.py                    `python -m beatsync.cli ...`
  scripts/
    download_datasets.py    fetch Ballroom audio + annotations
    benchmark.py            compare all three methods → report
extension/
  jsx/BeatSync.jsx          standalone ExtendScript (no install)
  panel/                    CEP panel (real plugin UI)
datasets/                   gitignored; see PROJECT_PLAN.md for sources
PROJECT_PLAN.md             milestones + scope
RESEARCH.md                 SOTA models, datasets, AE extensibility notes
```

## License

MIT, see `LICENSE`.
