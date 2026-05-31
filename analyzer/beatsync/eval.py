from __future__ import annotations

from typing import Iterable

import numpy as np


def f_measure(
    predicted: Iterable[float],
    reference: Iterable[float],
    tolerance: float = 0.07,
) -> dict:
    predicted = np.sort(np.asarray(predicted, dtype=float))
    reference = np.sort(np.asarray(reference, dtype=float))

    matched = np.zeros(len(reference), dtype=bool)
    tp = 0
    for p in predicted:
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
    result = {"f": f_measure(predicted, reference)}
    try:
        import mir_eval

        ref = np.asarray(reference, dtype=float)
        pred = np.asarray(predicted, dtype=float)
        scores = mir_eval.beat.evaluate(ref, pred)
        result["mir_eval"] = {k: float(v) for k, v in scores.items()}
    except ImportError:
        result["mir_eval"] = None
    return result
