"""Known BPM/key mini-corpus generated in-repo (no commercial audio)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import PyBridge  # noqa: E402
from generate_fixture import write_named_fixture

# ID | content | key | bpm | tolerance
# K1 A-minor triad + 120 BPM kicks | A minor | 120 | ±2
# K2 G-major triad + 100 BPM | G major | 100 | ±2
# K3 C-major triad + 140 BPM | C major | 140 | ±2
# K4 kick-only 174 BPM | key not required | 174 | ±3 after octave fold
# K5 70 BPM kicks | key not required | 70 | ±3 after octave fold
# K6 is the existing KS rotation unit tests in test_pybridge.py


@pytest.mark.parametrize(
    ("name", "expected_key", "expected_bpm", "bpm_tol"),
    [
        ("K1", "A minor", 120.0, 2.0),
        ("K2", "G major", 100.0, 2.0),
        ("K3", "C major", 140.0, 2.0),
    ],
)
def test_keyed_corpus(generated_dir: Path, name: str, expected_key: str, expected_bpm: float,
                      bpm_tol: float):
    path = write_named_fixture(generated_dir / f"{name}.wav", name)
    result = PyBridge.analyze_audio(str(path))
    assert result["key"] == expected_key
    assert abs(result["bpm"] - expected_bpm) <= bpm_tol
    assert result["analysis_sample_rate"] == 22050
    assert result["alternate_key"]


@pytest.mark.parametrize(
    ("name", "expected_bpm", "bpm_tol"),
    [
        ("K4", 174.0, 3.0),
        ("K5", 70.0, 3.0),
    ],
)
def test_tempo_fold_corpus(generated_dir: Path, name: str, expected_bpm: float, bpm_tol: float):
    path = write_named_fixture(generated_dir / f"{name}.wav", name)
    result = PyBridge.analyze_audio(str(path))
    assert abs(result["bpm"] - expected_bpm) <= bpm_tol
