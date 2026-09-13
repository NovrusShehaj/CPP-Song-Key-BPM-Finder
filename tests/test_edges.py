"""Edge, malformed, and resource-limit tests."""

from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import PyBridge  # noqa: E402
from generate_fixture import write_named_fixture, write_wav


def _write_pcm(path: Path, audio: np.ndarray, sr: int) -> Path:
    sf.write(path, audio, sr)
    return path


def test_empty_file_is_rejected(tmp_path: Path):
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        PyBridge.analyze_audio(str(empty))


def test_truncated_riff_is_decode_error(tmp_path: Path):
    truncated = tmp_path / "truncated.wav"
    truncated.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
    with pytest.raises(ValueError, match="Unsupported or corrupt audio"):
        PyBridge.analyze_audio(str(truncated))


def test_random_bytes_are_decode_error(tmp_path: Path):
    junk = tmp_path / "not-audio.txt"
    junk.write_text("this is not audio")
    with pytest.raises(ValueError, match="Unsupported or corrupt audio"):
        PyBridge.analyze_audio(str(junk))


def test_too_short_clip_is_rejected(tmp_path: Path):
    path = write_wav(tmp_path / "short.wav", duration=0.1, freqs=(220.0,), bpm=120.0, kick=False)
    with pytest.raises(ValueError, match="too short"):
        PyBridge.analyze_audio(str(path))


def test_digital_silence_is_rejected(generated_dir: Path):
    path = write_named_fixture(generated_dir / "silence.wav", "silence")
    with pytest.raises(ValueError, match="silent"):
        PyBridge.analyze_audio(str(path), min_duration_sec=2.0)


def test_file_size_cap_fails_before_decode(tmp_path: Path):
    huge = tmp_path / "huge.wav"
    huge.write_bytes(b"0" * 2048)
    with pytest.raises(ValueError, match="size limit"):
        PyBridge.analyze_audio(str(huge), max_bytes=512)


def test_duration_cap_analyzes_prefix(tmp_path: Path):
    path = write_wav(
        tmp_path / "long-enough.wav",
        duration=4.0,
        freqs=(220.0, 261.63, 329.63),
        bpm=120.0,
    )
    result = PyBridge.analyze_audio(str(path), max_duration_sec=2.5, min_duration_sec=2.0)
    assert result["duration_seconds"] == pytest.approx(2.5, abs=0.05)
    assert result["analysis_sample_rate"] == 22050


def test_stereo_44100_is_mixed_and_resampled(tmp_path: Path):
    sr = 44100
    duration = 8.0
    t = np.arange(int(sr * duration)) / sr
    left = 0.2 * np.sin(2 * np.pi * 220.0 * t)
    right = 0.2 * np.sin(2 * np.pi * 261.63 * t)
    stereo = np.stack([left, right], axis=1)
    path = _write_pcm(tmp_path / "stereo.wav", stereo.astype(np.float32), sr)
    result = PyBridge.analyze_audio(str(path), min_duration_sec=2.0)
    assert result["analysis_sample_rate"] == 22050
    assert result["sample_rate"] == 44100
    assert result["duration_seconds"] > 0


@pytest.mark.parametrize("sr", [8000, 96000])
def test_unusual_sample_rates_are_resampled(tmp_path: Path, sr: int):
    duration = 8.0
    t = np.arange(int(sr * duration)) / sr
    tone = 0.25 * (
        np.sin(2 * np.pi * 220.0 * t)
        + np.sin(2 * np.pi * 261.63 * t)
        + np.sin(2 * np.pi * 329.63 * t)
    ) / 3.0
    path = _write_pcm(tmp_path / f"rate-{sr}.wav", tone.astype(np.float32), sr)
    result = PyBridge.analyze_audio(str(path), min_duration_sec=2.0)
    assert result["analysis_sample_rate"] == 22050
    assert result["sample_rate"] == sr


def test_flac_roundtrip_if_supported(tmp_path: Path):
    path = tmp_path / "tone.flac"
    audio = 0.2 * np.sin(2 * np.pi * 220.0 * np.arange(22050 * 8) / 22050)
    try:
        sf.write(path, audio.astype(np.float32), 22050, format="FLAC")
    except Exception:
        pytest.skip("soundfile cannot write FLAC on this host")
    result = PyBridge.analyze_audio(str(path), min_duration_sec=2.0)
    assert result["analysis_sample_rate"] == 22050


def test_ogg_roundtrip_if_supported(tmp_path: Path):
    path = tmp_path / "tone.ogg"
    audio = 0.2 * np.sin(2 * np.pi * 220.0 * np.arange(22050 * 8) / 22050)
    try:
        sf.write(path, audio.astype(np.float32), 22050, format="OGG")
    except Exception:
        pytest.skip("soundfile cannot write OGG on this host")
    result = PyBridge.analyze_audio(str(path), min_duration_sec=2.0)
    assert result["analysis_sample_rate"] == 22050


def test_non_regular_fifo_is_rejected(tmp_path: Path):
    fifo = tmp_path / "audio.fifo"
    try:
        import os

        os.mkfifo(fifo)
    except OSError:
        pytest.skip("unable to create a FIFO on this host")
    with pytest.raises(ValueError, match="regular audio file"):
        PyBridge.analyze_audio(str(fifo))


def test_valid_generated_wav_header_is_riff(am_120_wav: Path):
    assert am_120_wav.read_bytes()[:4] == b"RIFF"
    with wave.open(str(am_120_wav), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getframerate() == 22050
