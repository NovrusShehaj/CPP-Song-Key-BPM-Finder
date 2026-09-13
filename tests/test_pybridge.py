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
    chroma = np.roll(PyBridge.MINOR_PROFILE, 9).reshape(-1, 1)
    key, score, confidence, alternate = PyBridge._estimate_key(chroma)
    assert key == "A minor"
    assert score == pytest.approx(1.0, abs=1e-9)
    assert confidence >= 0
    assert alternate


def test_estimate_key_matches_rotated_major_profile():
    chroma = np.roll(PyBridge.MAJOR_PROFILE, 7).reshape(-1, 1)
    key, score, confidence, alternate = PyBridge._estimate_key(chroma)
    assert key == "G major"
    assert score == pytest.approx(1.0, abs=1e-9)
    assert confidence >= 0
    assert alternate


def test_analyze_audio_missing_file_raises():
    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        PyBridge.analyze_audio("does/not/exist.wav")


def test_analyze_audio_rejects_directory():
    with pytest.raises(IsADirectoryError, match="directory"):
        PyBridge.analyze_audio(str(Path(__file__).resolve().parent))


def test_dsp_parameters_are_pinned():
    assert PyBridge.ANALYSIS_SAMPLE_RATE == 22050
    assert PyBridge.N_FFT == 2048
    assert PyBridge.HOP_LENGTH == 512
    assert PyBridge.WIN_LENGTH == 2048


@pytest.mark.parametrize("true_bpm", [70.0, 100.0, 120.0, 140.0, 174.0])
def test_refine_bpm_recovers_fractional_onset_period(true_bpm: float):
    sr = PyBridge.ANALYSIS_SAMPLE_RATE
    hop = PyBridge.HOP_LENGTH
    true_lag = (60.0 / true_bpm) * sr / hop
    quantized = 60.0 * sr / (hop * round(true_lag))
    lags = np.arange(96, dtype=float)
    ac = np.exp(-0.5 * ((lags - true_lag) / 1.25) ** 2)
    refined = PyBridge._refine_bpm_from_ac(ac, quantized, sr, hop)
    assert abs(refined - true_bpm) <= 0.5


def test_score_tempo_ac_interpolates_between_integer_lags():
    sr = PyBridge.ANALYSIS_SAMPLE_RATE
    hop = PyBridge.HOP_LENGTH
    true_bpm = 120.0
    true_lag = (60.0 / true_bpm) * sr / hop
    lags = np.arange(96, dtype=float)
    ac = np.exp(-0.5 * ((lags - true_lag) / 1.25) ** 2)
    score_true = PyBridge._score_tempo_ac(ac, sr, true_bpm, hop)
    lag_floor = math.floor(true_lag)
    lag_ceil = math.ceil(true_lag)
    frac = true_lag - lag_floor
    score_floor = PyBridge._score_tempo_ac(
        ac, sr, PyBridge._bpm_from_lag(lag_floor, sr, hop), hop
    )
    score_ceil = PyBridge._score_tempo_ac(
        ac, sr, PyBridge._bpm_from_lag(lag_ceil, sr, hop), hop
    )
    expected = float(ac[lag_floor] * (1.0 - frac) + ac[lag_ceil] * frac)
    assert score_true == pytest.approx(expected)
    assert score_true != score_floor
    assert score_true != score_ceil


def test_octave_choice_keeps_primary_when_subharmonic_is_slightly_stronger():
    candidates = [60.0, 120.0]
    scores = [0.92, 0.88]
    assert PyBridge._choose_tempo_octave(candidates, scores, 120.0) == 1


def test_octave_choice_switches_when_alternate_is_materially_stronger():
    primary = 100.0
    candidates = [100.0, 200.0]
    below = [1.0, PyBridge.TEMPO_OCTAVE_SWITCH_RATIO - 1e-6]
    above = [1.0, PyBridge.TEMPO_OCTAVE_SWITCH_RATIO + 1e-6]
    assert PyBridge._choose_tempo_octave(candidates, below, primary) == 0
    assert PyBridge._choose_tempo_octave(candidates, above, primary) == 1


def test_analyze_audio_on_sample(am_120_wav: Path):
    result = PyBridge.analyze_audio(str(am_120_wav))

    assert result["key"] == "A minor"
    assert 117 <= result["bpm"] <= 123
    assert result["analysis_sample_rate"] == 22050
    assert result["sample_rate"] > 0
    assert result["duration_seconds"] > 0
    assert result["alternate_key"]
    assert "bpm_candidates" in result
