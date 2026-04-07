# CPP Song Key + BPM Finder

`CPP-Song-Key-BPM-Finder` is a C++ command-line project that uses a Python analysis bridge (`librosa` + `numpy`) to detect:

1. tempo (BPM)
2. musical key (major/minor)
3. confidence and analysis metadata

## Why this version is more accurate

The project now uses a proper chroma-based key estimation pipeline with Krumhansl-Schmuckler key profiles instead of using tuning estimation as a key proxy.

## Repository layout

- `src/main.cpp`: single C++ entrypoint
- `include/bridge_runner.hpp`: C++ bridge execution utilities
- `scripts/PyBridge.py`: Python analysis engine
- `CMakeLists.txt`: build configuration
- `requirements.txt`: Python dependencies

## Prerequisites

- C++17 compiler (`g++`, `clang++`, or MSVC)
- CMake 3.16+
- Python 3.9+
- `pip`

## Setup

1. Install Python dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

2. Configure and build:

```bash
cmake -S . -B build
cmake --build build
```

## Usage

Run human-readable output:

```bash
KEY_BPM_PYTHON=.venv/bin/python ./build/Key-BpmFinder <audio_file>
```

Run JSON output from the same executable:

```bash
KEY_BPM_PYTHON=.venv/bin/python ./build/Key-BpmFinder --json <audio_file>
```

## Example output

Human-readable mode:

```text
BPM: 121.53
Key: A minor
Key score: 0.8652
Key confidence: 0.0421
Sample rate: 44100
Duration (seconds): 34.18
```

JSON mode:

```json
{"bpm": 121.53, "key": "A minor", "key_score": 0.8652, "key_confidence": 0.0421, "sample_rate": 44100, "duration_seconds": 34.18}
```

## Troubleshooting

- `Error: Audio file not found`: check the file path.
- `Error: Could not find PyBridge.py`: ensure `scripts/PyBridge.py` exists in the repository.
- `ModuleNotFoundError: No module named 'librosa'`: install dependencies with `python3 -m pip install -r requirements.txt`.
- If you use a virtual environment, set `KEY_BPM_PYTHON` to that Python executable.
- If an audio backend error appears, install `ffmpeg` and retry.

## Notes

- `Key-BpmFinder` copies `scripts/PyBridge.py` into the build output directory automatically.
- Key estimation is probabilistic; confidence is included so low-confidence detections are visible.
