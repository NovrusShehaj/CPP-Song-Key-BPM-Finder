#!/usr/bin/env python3
"""Synthesize short musical WAV fixtures with the standard library only."""

from __future__ import annotations

import argparse
import math
import wave
from pathlib import Path

NOTE_FREQS = {
    "A minor": (220.00, 261.6256, 329.6276),
    "G major": (196.00, 246.9417, 293.6648),
    "C major": (261.6256, 329.6276, 392.00),
}

DEFAULT_SR = 22050
DEFAULT_DURATION = 12.0


def _sample_at(
    index: int,
    sr: int,
    freqs: tuple[float, ...],
    bpm: float,
    kick: bool,
    kick_gain: float,
) -> int:
    t = index / sr
    sample = 0.0
    if freqs:
        sample = sum(math.sin(2.0 * math.pi * freq * t) for freq in freqs) / len(freqs)
        # Peak the triad on the kick (cos), not a quarter-beat later (sin).
        pulse = 0.55 + 0.45 * max(0.0, math.cos(2.0 * math.pi * (bpm / 60.0) * t))
        sample *= 0.32 * pulse
    beat_period = max(int(sr * 60.0 / bpm), 1)
    pos = index % beat_period
    if kick and pos < int(0.04 * sr):
        decay = 1.0 - (pos / max(int(0.04 * sr), 1))
        sample += kick_gain * decay * math.sin(2.0 * math.pi * 55.0 * t)
        if pos < int(0.004 * sr):
            sample += 0.25 * kick_gain * decay
    sample = max(-1.0, min(1.0, sample))
    return int(sample * 32767.0)


def write_wav(
    path: Path,
    *,
    sr: int = DEFAULT_SR,
    duration: float = DEFAULT_DURATION,
    freqs: tuple[float, ...] = (),
    bpm: float = 120.0,
    kick: bool = True,
    kick_gain: float = 0.45,
    channels: int = 1,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame_count = int(sr * duration)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        frames = bytearray()
        for index in range(frame_count):
            value = _sample_at(index, sr, freqs, bpm, kick, kick_gain)
            encoded = value.to_bytes(2, byteorder="little", signed=True)
            frames.extend(encoded * channels)
        handle.writeframes(frames)
    return path


def write_named_fixture(path: Path, name: str) -> Path:
    if name == "K1":
        return write_wav(path, freqs=NOTE_FREQS["A minor"], bpm=120.0)
    if name == "K2":
        return write_wav(path, freqs=NOTE_FREQS["G major"], bpm=100.0)
    if name == "K3":
        return write_wav(path, freqs=NOTE_FREQS["C major"], bpm=140.0)
    if name == "K4":
        return write_wav(path, freqs=(), bpm=174.0, kick=True, kick_gain=0.95)
    if name == "K5":
        return write_wav(path, freqs=(), bpm=70.0, kick=True, kick_gain=0.95)
    if name == "silence":
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "w") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(DEFAULT_SR)
            handle.writeframes(b"\x00\x00" * int(DEFAULT_SR * 5))
        return path
    raise ValueError(f"Unknown fixture name: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate synthetic Key/BPM WAV fixtures.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / ".generated" / "test-tone-a-minor-120bpm.wav",
    )
    parser.add_argument("--name", default="K1", help="Fixture id: K1, K2, K3, K4, K5, silence")
    args = parser.parse_args()
    write_named_fixture(args.output, args.name)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
