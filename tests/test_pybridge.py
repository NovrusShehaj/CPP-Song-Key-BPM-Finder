"""Unit tests for the Python analysis bridge."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import PyBridge  # noqa: E402


def test_normalize_produces_unit_vector():
    normalized = PyBridge._normalize(np.array([3.0, 4.0]))
    assert math.isclose(float(np.linalg.norm(normalized)), 1.0, rel_tol=1e-9)


def test_normalize_rejects_silence():
    with pytest.raises(ValueError):
        PyBridge._normalize(np.zeros(12))


def test_estimate_key_matches_rotated_minor_profile():
    # Rotating the minor profile by 9 semitones (C -> A) should be identified as A minor.
    chroma = np.roll(PyBridge.MINOR_PROFILE, 9).reshape(-1, 1)
    key, score, confidence = PyBridge._estimate_key(chroma)
    assert key == "A minor"
    assert score == pytest.approx(1.0, abs=1e-9)
    assert confidence >= 0


def test_estimate_key_matches_rotated_major_profile():
    # Rotating the major profile by 7 semitones (C -> G) should be identified as G major.
    chroma = np.roll(PyBridge.MAJOR_PROFILE, 7).reshape(-1, 1)
    key, score, confidence = PyBridge._estimate_key(chroma)
    assert key == "G major"
    assert score == pytest.approx(1.0, abs=1e-9)
    assert confidence >= 0


def test_analyze_audio_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        PyBridge.analyze_audio("does/not/exist.wav")


def test_analyze_audio_rejects_directory():
    with pytest.raises(IsADirectoryError):
        PyBridge.analyze_audio(str(Path(__file__).resolve().parent))


def test_analyze_audio_on_sample():
    sample = Path(__file__).resolve().parents[1] / "samples" / "test-tone-a-minor-120bpm.wav"
    result = PyBridge.analyze_audio(str(sample))

    assert result["key"] == "A minor"
    assert 100 < result["bpm"] < 140
    assert result["sample_rate"] > 0
    assert result["duration_seconds"] > 0
