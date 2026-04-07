#!/usr/bin/env python3
"""Python bridge for audio BPM and key estimation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import librosa
import numpy as np

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


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    if norm == 0:
        raise ValueError("Audio content is silent or too weak for reliable key estimation.")
    return vector / norm


def _estimate_key(chroma: np.ndarray) -> tuple[str, float, float]:
    chroma_vector = _normalize(np.mean(chroma, axis=1))
    base_major = _normalize(MAJOR_PROFILE)
    base_minor = _normalize(MINOR_PROFILE)

    best_key = ""
    best_score = float("-inf")
    second_best_score = float("-inf")

    for shift, key_name in enumerate(KEY_NAMES):
        major_profile = np.roll(base_major, shift)
        major_score = float(np.dot(chroma_vector, major_profile))
        if major_score > best_score:
            second_best_score = best_score
            best_score = major_score
            best_key = f"{key_name} major"
        elif major_score > second_best_score:
            second_best_score = major_score

        minor_profile = np.roll(base_minor, shift)
        minor_score = float(np.dot(chroma_vector, minor_profile))
        if minor_score > best_score:
            second_best_score = best_score
            best_score = minor_score
            best_key = f"{key_name} minor"
        elif minor_score > second_best_score:
            second_best_score = minor_score

    confidence = max(0.0, best_score - second_best_score)
    return best_key, best_score, confidence


def analyze_audio(file_path: str) -> dict[str, float | str]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    if path.is_dir():
        raise IsADirectoryError(f"Expected an audio file but got a directory: {file_path}")

    y, sr = librosa.load(file_path, sr=None, mono=True)
    if y.size == 0:
        raise ValueError("Audio file contains no samples.")

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo).reshape(-1)[0])
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key, key_score, key_confidence = _estimate_key(chroma)
    duration_seconds = float(librosa.get_duration(y=y, sr=sr))

    return {
        "bpm": bpm,
        "key": key,
        "key_score": key_score,
        "key_confidence": key_confidence,
        "sample_rate": int(sr),
        "duration_seconds": duration_seconds,
    }


def _format_human_readable(result: dict[str, float | str]) -> str:
    return (
        f"BPM: {result['bpm']:.2f}\n"
        f"Key: {result['key']}\n"
        f"Key score: {result['key_score']:.4f}\n"
        f"Key confidence: {result['key_confidence']:.4f}\n"
        f"Sample rate: {result['sample_rate']}\n"
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
    args = parser.parse_args()

    try:
        result = analyze_audio(args.audio_file)
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result))
    else:
        print(_format_human_readable(result), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
