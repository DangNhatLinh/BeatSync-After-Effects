# Research Notes — BeatSync

State of the art (as of 2026) and the architectural choices that come out of it.

---

## Beat tracking — what to use

### Classical baseline: librosa

`librosa.beat.beat_track` (Ellis 2007) — onset-strength envelope + dynamic programming
against an estimated global tempo. Strong on steady 4/4, weak on tempo changes, swing,
classical, and tracks with sparse percussion. Ships in any Python environment, no GPU.
This is our **baseline** — every ML result has to beat it.

### Pretrained neural: Beat This!

[CPJKU/beat_this](https://github.com/CPJKU/beat_this), ISMIR 2024.

- Architecture: alternating convolution and transformer blocks over mel-spec patches in frequency *and* time. Tracks beats and downbeats jointly.
- Trained without the usual Dynamic Bayesian Network (DBN) postprocessing — generalizes much better to non-4/4 / classical / time-signature changes than `madmom`.
- Maintained, pip-installable, supports Python ≥ 3.10, runs on CPU or CUDA.
- Install: `pip install https://github.com/CPJKU/beat_this/archive/main.zip`
- Usage:
  ```python
  from beat_this.inference import File2Beats
  f2b = File2Beats(checkpoint_path="final0", device="cpu", dbn=False)
  beats, downbeats = f2b("song.wav")   # both are np.ndarray of seconds
  ```

This is what `analyzer/beatsync/ml.py` wraps.

### Why not madmom?

`madmom` was the standard from ~2016. As of 2025 it's effectively unmaintained for modern
Python — PyPI build is capped at Python < 3.10, the GitHub `main` branch installs on
3.10/3.11 but breaks on 3.12 with a circular import. Avoid as a primary dependency.

### Other 2024–2025 papers worth knowing

- **BeatNet** (Heydari & Duan, 2021): real-time online beat/downbeat tracker. Good if we ever want live-playback beat detection inside AE.
- **BeatFM** (2025): pretrained music foundation model + multi-dimensional aggregation. SOTA but heavy.
- **HingeNet** (2025): parameter-efficient fine-tuning on a foundation model, harmonic-aware. Promising if we want to fine-tune for specific genres without retraining everything.

For our purposes, **Beat This! is the right ceiling** — strong, open, runnable, and a
plausible architecture to take inspiration from when we train our own.

---

## After Effects extensibility — what to target

| Framework | Status (2026) | Use it for BeatSync? |
| --- | --- | --- |
| **ExtendScript (`.jsx`)** | Still supported, used everywhere | **YES** — our no-install fallback. Can place markers, read files, JSON-parse. |
| **CEP (HTML/JS panel + Node-like `window.cep.process`)** | Still supported in AE, no announced deprecation date for AE specifically. | **YES** — our main "plugin" target. Lets us shell out to Python and build a real UI. |
| **UXP for After Effects** | Rolling out, but Adobe has confirmed it **won't support webview, WebGL, or web workers**, and CEP→UXP porting is not directly possible. | **No** — too immature / too restrictive for this project. Revisit in 2027. |

### Why CEP + .jsx is the right split

- CEP gives us a native-looking panel with real buttons and the ability to spawn the
  Python analyzer via `window.cep.process.createProcess`.
- The host-side `.jsx` does the actual AE work (selecting layers, placing markers) and
  is identical to the standalone script. So users who can't or won't install a CEP
  bundle can still get value by running `BeatSync.jsx` directly.
- CEP bundles are signed (`ZXPSignCmd`) and installed via tools like Anastasiy's
  Extension Manager or ZXP Installer. That's the standard pro-AE plugin distribution
  story (aescripts.com, Battle Axe, etc. all ship this way).

### Marker API cheat sheet

```javascript
app.beginUndoGroup("BeatSync: place markers");
var markerProp = layer.property("Marker");
var m = new MarkerValue("beat 12");
m.duration = 0;          // point marker
m.label = 1;             // 0..16, AE label colors
markerProp.setValueAtTime(timeInSeconds, m);
app.endUndoGroup();
```

Markers can live on **any** layer or on a comp's null layer. Convention: place them on
the audio layer itself so they travel with the asset.

---

## Datasets (training)

See `PROJECT_PLAN.md` § Datasets. All standard beat-tracking benchmarks are research-only
licensed — fine for a personal project, do not redistribute the audio.

---

## Open questions

1. Do we expose tempo estimation as its own button (some editors just want the BPM)?
2. For the trained model, do we predict beat probability per-frame and pick peaks, or
   directly regress inter-beat-intervals? Per-frame + peak-picking is what `Beat This!`
   does and is easier to evaluate frame-wise, so probably that.
3. Do we want section detection (`intro/verse/drop/outro`) in v1? It's a separate model
   and a separate dataset (SALAMI). Punt to M5 unless time allows.
