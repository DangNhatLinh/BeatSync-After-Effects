"""Evaluation metrics for beat tracking.

Standard MIR metric is F-measure with a ±70 ms tolerance window (Davies & Plumbley,
2007). CMLt / AMLt (continuity-based) are also standard but more involved — we
delegate those to `mir_eval` if it's installed.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


def f_measure(
    predicted: Iterable[float],
    reference: Iterable[float],
    tolerance: float = 0.07,
) -> dict:
    """Greedy F-measure: each predicted beat is matched to at most one reference beat
    within `tolerance` seconds. Same as mir_eval.beat.f_measure for sane inputs."""
    predicted = np.sort(np.asarray(predicted, dtype=float))
    reference = np.sort(np.asarray(reference, dtype=float))

    matched = np.zeros(len(reference), dtype=bool)
    tp = 0
    for p in predicted:
        # find nearest unmatched reference within tolerance
        diffs = np.abs(reference - p)
        diffs[matched] = np.inf
        if len(diffs) and diffs.min() <= tolerance:
            matched[int(np.argmin(diffs))] = True
            tp += 1

    fp = len(predicted) - tp
    fn = len(reference) - tp
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f = 2 * precision * recall / max(precision + recall, 1e-9)
    return {
        "precision": float(precision),
        "recall": float(recall),
        "f_measure": float(f),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
    }


def evaluate(predicted, reference) -> dict:
    """Full eval bundle. Adds CMLt/AMLt/etc when mir_eval is available."""
    result = {"f": f_measure(predicted, reference)}
    try:
        import mir_eval  # type: ignore

        ref = np.asarray(reference, dtype=float)
        pred = np.asarray(predicted, dtype=float)
        scores = mir_eval.beat.evaluate(ref, pred)
        result["mir_eval"] = {k: float(v) for k, v in scores.items()}
    except ImportError:
        result["mir_eval"] = None
    return result
