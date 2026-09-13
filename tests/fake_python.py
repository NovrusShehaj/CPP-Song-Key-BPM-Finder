#!/usr/bin/env python3
"""Stub interpreter for C++ bridge tests. Does not import librosa."""

from __future__ import annotations

import json
import os
import sys
import time


def main() -> int:
    mode = os.environ.get("KEY_BPM_FAKE_MODE", "json")
    if mode == "sleep":
        time.sleep(float(os.environ.get("KEY_BPM_FAKE_SLEEP", "30")))
        return 0
    if mode == "fail":
        print("synthetic failure from stub", file=sys.stderr)
        return 1
    if mode == "signal":
        os.kill(os.getpid(), 9)
        return 1
    if mode == "warn":
        print("UserWarning: injected warning", file=sys.stderr)

    payload = {
        "bpm": 120.0,
        "key": "A minor",
        "key_score": 0.9,
        "key_confidence": 0.2,
        "alternate_key": "C major",
        "sample_rate": 22050,
        "analysis_sample_rate": 22050,
        "duration_seconds": 8.0,
    }
    if "--json" in sys.argv:
        print(json.dumps(payload))
    else:
        print("BPM: 120.00")
        print("Key: A minor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
