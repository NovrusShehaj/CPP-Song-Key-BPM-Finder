#!/usr/bin/env python3
"""Python analysis engine for tempo (BPM) and musical key estimation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import librosa
import numpy as np
import soundfile as sf

KEY_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

# Krumhansl-Schmuckler key profiles.
MAJOR_PROFILE = np.array(
    [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88],
    dtype=float,
)
MINOR_PROFILE = np.array(
    [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17],
    dtype=float,
)

# Pinned DSP parameters so chroma/tempo do not silently follow librosa defaults.
ANALYSIS_SAMPLE_RATE = 22050
N_FFT = 2048
HOP_LENGTH = 512
WIN_LENGTH = 2048
DEFAULT_MAX_FILE_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_DURATION_SEC = 600.0
DEFAULT_MIN_DURATION_SEC = 2.0
DEFAULT_SILENCE_RMS = 1e-4
BPM_RANGE = (56.0, 200.0)
# beat_track reports a discrete onset-AC lag. At hop=512 / 22050 Hz the
# nearest bins sit a few BPM off common tempi (e.g. 117.45 vs 120).
TEMPO_REFINE_REL_WINDOW = 0.10
# Raw AC[2T] is structurally close to AC[T] for any pulse train, so a
# slower octave can win a near-tie. Keep the refined beat_track tempo
# unless another candidate is materially stronger.
TEMPO_OCTAVE_SWITCH_RATIO = 1.50

# soundfile is the explicit decode/probe backend for librosa.load on WAV/FLAC/OGG.


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _debug_enabled() -> bool:
    return bool(os.environ.get("KEYBPM_DEBUG"))


def _progress(message: str, enabled: bool) -> None:
    if enabled:
        print(message, file=sys.stderr)


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError("Audio content is silent or too weak for reliable key estimation.")
    return vector / norm


def _estimate_key(chroma: np.ndarray) -> tuple[str, float, float, str]:
    chroma_vector = _normalize(np.mean(chroma, axis=1))
    base_major = _normalize(MAJOR_PROFILE)
    base_minor = _normalize(MINOR_PROFILE)

    best_key = ""
    alternate_key = ""
    best_score = float("-inf")
    second_best_score = float("-inf")

    for shift, key_name in enumerate(KEY_NAMES):
        for mode, base_profile in (("major", base_major), ("minor", base_minor)):
            profile = np.roll(base_profile, shift)
            score = float(np.dot(chroma_vector, profile))
            label = f"{key_name} {mode}"
            if score > best_score:
                alternate_key = best_key
                second_best_score = best_score
                best_score = score
                best_key = label
            elif score > second_best_score:
                second_best_score = score
                alternate_key = label

    confidence = max(0.0, best_score - second_best_score)
    return best_key, best_score, confidence, alternate_key


def _confidence_label(confidence: float) -> str:
    if confidence < 0.05:
        return "low"
    if confidence < 0.12:
        return "medium"
    return "high"


def _tempo_candidates(raw_bpm: float) -> list[float]:
    candidates: list[float] = []
    for scale in (0.5, 1.0, 2.0):
        value = raw_bpm * scale
        if BPM_RANGE[0] <= value <= BPM_RANGE[1]:
            candidates.append(float(value))
    if not candidates:
        candidates.append(float(raw_bpm))
    return candidates


def _onset_autocorr(onset_env: np.ndarray) -> np.ndarray:
    if onset_env.size < 2:
        return np.zeros(1, dtype=float)
    ac = np.correlate(onset_env, onset_env, mode="full")
    ac = ac[onset_env.size - 1 :].astype(float, copy=False)
    if ac[0] > 0:
        ac = ac / ac[0]
    return ac


def _lag_from_bpm(bpm: float, sr: int, hop_length: int) -> float:
    return (60.0 / max(bpm, 1e-6)) * float(sr) / float(hop_length)


def _bpm_from_lag(lag: float, sr: int, hop_length: int) -> float:
    return 60.0 * float(sr) / (float(hop_length) * max(lag, 1e-6))


def _parabolic_peak_offset(y0: float, y1: float, y2: float) -> float:
    denom = y0 - 2.0 * y1 + y2
    if abs(denom) < 1e-12:
        return 0.0
    delta = 0.5 * (y0 - y2) / denom
    if abs(delta) >= 1.0:
        return 0.0
    return float(delta)


def _refine_bpm_from_ac(
    ac: np.ndarray,
    raw_bpm: float,
    sr: int,
    hop_length: int,
    rel_window: float = TEMPO_REFINE_REL_WINDOW,
) -> float:
    """Move a hop-quantized tempo onto the local onset-AC peak."""
    if raw_bpm <= 0.0 or ac.size < 3:
        return float(raw_bpm)
    center = _lag_from_bpm(raw_bpm, sr, hop_length)
    lo = max(1, int(np.floor(center * (1.0 - rel_window))))
    hi = min(ac.size - 2, int(np.ceil(center * (1.0 + rel_window))))
    if hi < lo:
        return float(raw_bpm)
    peak = lo + int(np.argmax(ac[lo : hi + 1]))
    refined_lag = float(peak) + _parabolic_peak_offset(
        float(ac[peak - 1]), float(ac[peak]), float(ac[peak + 1])
    )
    refined_bpm = _bpm_from_lag(refined_lag, sr, hop_length)
    low = raw_bpm * (1.0 - rel_window)
    high = raw_bpm * (1.0 + rel_window)
    if refined_bpm < low or refined_bpm > high:
        return float(raw_bpm)
    return float(refined_bpm)


def _sample_ac(ac: np.ndarray, lag: float) -> float:
    if ac.size < 2 or not np.isfinite(lag):
        return 0.0
    if lag < 1.0 or lag >= float(ac.size - 1):
        idx = int(round(lag))
        if idx < 1 or idx >= ac.size:
            return 0.0
        return float(ac[idx])
    lo = int(np.floor(lag))
    frac = float(lag - lo)
    return float(ac[lo] * (1.0 - frac) + ac[lo + 1] * frac)


def _score_tempo_ac(ac: np.ndarray, sr: int, bpm: float, hop_length: int) -> float:
    if ac.size < 2 or bpm <= 0.0:
        return 0.0
    return _sample_ac(ac, _lag_from_bpm(bpm, sr, hop_length))


def _choose_tempo_octave(
    candidates: list[float],
    scores: list[float],
    primary_bpm: float,
    *,
    switch_ratio: float = TEMPO_OCTAVE_SWITCH_RATIO,
) -> int:
    """Keep the refined tracker octave unless another score is materially stronger."""
    if not candidates:
        return 0
    if len(candidates) == 1 or primary_bpm <= 0.0:
        return int(np.argmax(np.asarray(scores, dtype=float))) if scores else 0
    primary_index = min(
        range(len(candidates)),
        key=lambda i: abs(candidates[i] / primary_bpm - 1.0),
    )
    primary_score = max(float(scores[primary_index]), 0.0)
    best_index = primary_index
    best_score = primary_score
    threshold = primary_score * switch_ratio if primary_score > 1e-12 else 0.0
    for index, score in enumerate(scores):
        value = float(score)
        if index == primary_index:
            continue
        if value >= threshold and value > best_score:
            best_index = index
            best_score = value
    return best_index


def _select_bpm(
    y: np.ndarray,
    sr: int,
    *,
    hop_length: int = HOP_LENGTH,
    n_fft: int = N_FFT,
    win_length: int = WIN_LENGTH,
) -> tuple[float, list[float], float]:
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
    raw_bpm = float(np.atleast_1d(tempo).reshape(-1)[0])
    onset_env = librosa.onset.onset_strength(
        y=y, sr=sr, hop_length=hop_length, n_fft=n_fft, win_length=win_length
    )
    ac = _onset_autocorr(onset_env)
    refined_raw = _refine_bpm_from_ac(ac, raw_bpm, sr, hop_length)
    candidates = _tempo_candidates(refined_raw)
    scores = [_score_tempo_ac(ac, sr, candidate, hop_length) for candidate in candidates]
    best_index = _choose_tempo_octave(candidates, scores, refined_raw)
    best_bpm = candidates[best_index]
    if len(scores) > 1:
        ordered = sorted(scores, reverse=True)
        confidence = max(0.0, (ordered[0] - ordered[1]) / (ordered[0] + 1e-12))
    else:
        confidence = 1.0
    return best_bpm, candidates, confidence


def _probe_native(path: Path) -> tuple[int | None, float | None]:
    try:
        info = sf.info(str(path))
        return int(info.samplerate), float(info.duration)
    except Exception:
        return None, None


def analyze_audio(
    file_path: str,
    *,
    max_bytes: int | None = None,
    max_duration_sec: float | None = None,
    min_duration_sec: float | None = None,
    progress: bool = False,
) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    if path.is_dir():
        raise IsADirectoryError(f"Expected an audio file but got a directory: {file_path}")
    if not path.is_file():
        raise ValueError(f"Expected a regular audio file: {file_path}")

    size = path.stat().st_size
    if size == 0:
        raise ValueError(f"Audio file is empty: {file_path}")

    byte_limit = max_bytes if max_bytes is not None else _env_int(
        "KEY_BPM_MAX_BYTES", DEFAULT_MAX_FILE_BYTES
    )
    duration_limit = (
        max_duration_sec
        if max_duration_sec is not None
        else _env_float("KEY_BPM_MAX_DURATION_SEC", DEFAULT_MAX_DURATION_SEC)
    )
    duration_floor = (
        min_duration_sec
        if min_duration_sec is not None
        else _env_float("KEY_BPM_MIN_DURATION_SEC", DEFAULT_MIN_DURATION_SEC)
    )

    if size > byte_limit:
        raise ValueError(
            f"Audio file exceeds size limit ({byte_limit} bytes): {file_path}"
        )

    native_sr, header_duration = _probe_native(path)
    if header_duration is not None and header_duration + 1e-6 < duration_floor:
        raise ValueError(
            f"Audio is too short for reliable analysis ({header_duration:.3f}s)."
        )
    _progress("Loading…", progress)
    load_started = time.perf_counter()
    try:
        y, sr = librosa.load(
            file_path,
            sr=ANALYSIS_SAMPLE_RATE,
            mono=True,
            duration=duration_limit,
        )
    except Exception as exc:
        raise ValueError(f"Unsupported or corrupt audio: {exc}") from exc
    load_elapsed = time.perf_counter() - load_started

    if y.size == 0:
        raise ValueError("Audio file contains no samples.")

    duration_seconds = float(librosa.get_duration(y=y, sr=sr))
    if duration_seconds + 1e-6 < duration_floor:
        raise ValueError(
            f"Audio is too short for reliable analysis ({duration_seconds:.3f}s)."
        )

    rms = float(np.sqrt(np.mean(np.square(y))))
    if rms < DEFAULT_SILENCE_RMS:
        raise ValueError("Audio content is too silent for reliable analysis.")

    _progress("Estimating tempo…", progress)
    tempo_started = time.perf_counter()
    bpm, bpm_candidates, bpm_confidence = _select_bpm(
        y,
        sr,
        hop_length=HOP_LENGTH,
        n_fft=N_FFT,
        win_length=WIN_LENGTH,
    )
    tempo_elapsed = time.perf_counter() - tempo_started

    _progress("Estimating key…", progress)
    key_started = time.perf_counter()
    try:
        tuning = float(librosa.estimate_tuning(y=y, sr=sr, n_fft=N_FFT))
    except Exception:
        tuning = 0.0
    chroma = librosa.feature.chroma_cqt(
        y=y,
        sr=sr,
        hop_length=HOP_LENGTH,
        tuning=tuning,
    )
    key, key_score, key_confidence, alternate_key = _estimate_key(chroma)
    key_elapsed = time.perf_counter() - key_started

    if _debug_enabled():
        print(
            f"timings load={load_elapsed:.3f}s tempo={tempo_elapsed:.3f}s "
            f"key={key_elapsed:.3f}s n_fft={N_FFT} hop_length={HOP_LENGTH} "
            f"win_length={WIN_LENGTH}",
            file=sys.stderr,
        )

    return {
        "bpm": bpm,
        "bpm_candidates": bpm_candidates,
        "bpm_confidence": bpm_confidence,
        "key": key,
        "alternate_key": alternate_key,
        "key_score": key_score,
        "key_confidence": key_confidence,
        "sample_rate": int(native_sr) if native_sr is not None else int(sr),
        "analysis_sample_rate": int(sr),
        "duration_seconds": duration_seconds,
    }


def _format_human_readable(result: dict[str, Any]) -> str:
    label = _confidence_label(float(result["key_confidence"]))
    candidates = ", ".join(f"{value:.2f}" for value in result["bpm_candidates"])
    return (
        f"BPM: {result['bpm']:.2f}\n"
        f"BPM candidates: {candidates}\n"
        f"Key: {result['key']}\n"
        f"Alternate key: {result['alternate_key']}\n"
        f"Key score: {result['key_score']:.4f}\n"
        f"Key confidence: {result['key_confidence']:.4f} ({label}, unvalidated)\n"
        f"Sample rate: {result['sample_rate']}\n"
        f"Analysis sample rate: {result['analysis_sample_rate']}\n"
        f"Duration (seconds): {result['duration_seconds']:.2f}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze an audio file and estimate BPM and musical key."
    )
    parser.add_argument("audio_file", help="Path to the audio file.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print progress on stderr.",
    )
    args = parser.parse_args()

    try:
        result = analyze_audio(
            args.audio_file,
            progress=(not args.json) or args.verbose,
        )
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except (FileNotFoundError, IsADirectoryError, ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        if _debug_enabled():
            raise
        print(str(error), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result))
    else:
        print(_format_human_readable(result), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
