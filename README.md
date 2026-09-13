# CPP Song Key + BPM Finder

![CI](https://github.com/NovrusShehaj/CPP-Song-Key-BPM-Finder/actions/workflows/ci.yml/badge.svg)

POSIX command-line tool. A thin C++ process wrapper launches `scripts/PyBridge.py`,
which uses `librosa` + `numpy` + `soundfile` to estimate tempo (BPM) and musical key.

This is a **v0.1** prototype CLI, not a validated commercial analyzer. Key detection
uses Krumhansl–Schmuckler profiles on CQT chroma. That is a different method than an
older tuning-as-key proxy in earlier revisions of this repo; it is **not** a claim of
measured accuracy on a labeled music corpus.

## Platform support

| Platform | Status |
|---|---|
| Linux | Supported; tested in GitHub Actions (`ubuntu-latest`) |
| macOS | Best-effort POSIX; CI job is provided but not a release guarantee |
| Windows / MSVC | **Not supported.** The runner uses `posix_spawnp` |

## Prerequisites

- C++17 compiler (`g++` or `clang++`)
- CMake 3.16+
- Python 3.10–3.12 (3.11 is the CI baseline). CPython 3.14 is **unsupported** until a job proves `librosa`/`numba` work.
- `pip`

Optional: `ffmpeg` for formats `soundfile` cannot decode (for example many MP3 files).

## Repository layout

- `src/main.cpp`: CLI (`--json`, `--help`, `--version`, `-v`)
- `src/bridge_runner.cpp`: POSIX process runner, discovery, timeouts
- `include/bridge_runner.hpp`: public C++ API
- `scripts/PyBridge.py`: analysis engine
- `tests/`: pytest suite, generated fixtures, CLI stub tests, integration script
- `CMakeLists.txt`: POSIX build, optional sanitizers, install rules

## Setup

Use a project-local virtualenv. Set `KEY_BPM_PYTHON` to that interpreter when you
run the binary so it does not pick up a system `python3` without `librosa`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

## Usage

Human-readable output:

```bash
KEY_BPM_PYTHON=.venv/bin/python ./build/Key-BpmFinder <audio_file>
```

JSON output (`--json` may appear before or after the path):

```bash
KEY_BPM_PYTHON=.venv/bin/python ./build/Key-BpmFinder --json <audio_file>
KEY_BPM_PYTHON=.venv/bin/python ./build/Key-BpmFinder <audio_file> --json
```

```bash
./build/Key-BpmFinder --help
./build/Key-BpmFinder --version
```

`--json` without a file path prints usage and exits 2; it is not treated as a filename.

## JSON fields

Success stdout is a single JSON object. Warnings go to stderr and must not appear on stdout.

| Field | Meaning |
|---|---|
| `bpm` | Selected tempo after local onset-period refinement and ½×/1×/2× octave fold in 56–200 BPM |
| `bpm_candidates` | Candidate tempi that were scored |
| `bpm_confidence` | Uncalibrated gap between the top two tempo scores |
| `key` | Best of 24 major/minor names |
| `alternate_key` | Second-best key (relative-mode ambiguity is common) |
| `key_score` | Cosine similarity of mean chroma to the KS profile |
| `key_confidence` | Score gap to the second-best key; **not** a probability |
| `sample_rate` | Native file rate from `soundfile.info` when available |
| `analysis_sample_rate` | Fixed analysis rate (`22050`) |
| `duration_seconds` | Duration actually analyzed (capped) |

Human mode also prints `low|medium|high` confidence labels. Those cutovers are
temporary and **unvalidated**.

## Limits and safety

| Limit | Default | Override |
|---|---|---|
| Analysis sample rate | 22050 Hz mono | not configurable |
| File size | 50 MiB | `KEY_BPM_MAX_BYTES` |
| Analyzed duration | first 600 s | `KEY_BPM_MAX_DURATION_SEC` |
| Minimum duration | 2 s | `KEY_BPM_MIN_DURATION_SEC` |
| Child wall time | 120 s then SIGKILL | `KEY_BPM_TIMEOUT_SEC` |

Non-regular files (directories, FIFOs, devices) are rejected before decode.

## Environment

| Variable | Role |
|---|---|
| `KEY_BPM_PYTHON` | Interpreter used to run `PyBridge.py` (required when using a venv) |
| `KEY_BPM_BRIDGE` | Override path to `PyBridge.py` |
| `KEY_BPM_TIMEOUT_SEC` | Child timeout |
| `KEY_BPM_MAX_BYTES` | File-size cap (C++ and Python) |
| `KEYBPM_DEBUG` | Extra timings and paths on stderr |

Bridge discovery order: `KEY_BPM_BRIDGE`, directory of the real executable
(`/proc/self/exe` on Linux), `share/keybpm/PyBridge.py` next to the install prefix,
then the current working directory. A decoy `scripts/PyBridge.py` in cwd does not
win over the binary-adjacent or installed script.

## Formats

- WAV, FLAC, OGG: via `soundfile` / libsndfile
- MP3 and other containers: only if `ffmpeg`/`audioread` can decode them; otherwise the tool reports `Unsupported or corrupt audio`

## Testing

```bash
.venv/bin/pip install -r requirements-dev.txt
cmake -S . -B build
cmake --build build
mkdir -p .tmp/pytest
KEY_BPM_PYTHON=.venv/bin/python \
  .venv/bin/pytest tests/ -v --basetemp="$PWD/.tmp/pytest"
KEY_BPM_PYTHON=.venv/bin/python bash tests/integration_test.sh
```

Fixtures are generated; see [samples/README.md](samples/README.md). Do not point
docs or CI at a missing binary WAV.

Optional sanitizer build (C++ runner only):

```bash
cmake -S . -B build-asan -DKEYBPM_SANITIZE=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build-asan
```

## Install prefix

```bash
cmake --install build --prefix "$PWD/.tmp/prefix"
KEY_BPM_PYTHON=.venv/bin/python .tmp/prefix/bin/Key-BpmFinder --json <audio_file>
```

The install layout is `bin/Key-BpmFinder` plus `share/keybpm/PyBridge.py`.
A matching Python environment is still required. There is no one-file bundle.

## Troubleshooting

- `Error: Audio file does not exist`: the path is missing (C++ check).
- `Error: Expected an audio file, but received a directory`: the path is a directory.
- `Error: Expected a regular audio file`: FIFO/device/non-regular input.
- `Error: Audio file is empty`: zero-byte file.
- `Error: Audio file exceeds size limit`: over `KEY_BPM_MAX_BYTES`.
- `Error: Audio file not found`: Python-only path when C++ checks are bypassed.
- `Error: Unsupported or corrupt audio`: decoder failure or unknown format.
- `Error: Audio is too short for reliable analysis`: under the minimum duration.
- `Error: Audio content is too silent for reliable analysis`: RMS gate.
- `Error: Could not find PyBridge.py`: the bridge script is not next to the binary, in `share/keybpm`, or in `scripts/`.
- `Error: Audio analysis timed out`: child exceeded `KEY_BPM_TIMEOUT_SEC`.
- `ModuleNotFoundError: No module named 'librosa'`: install requirements and set `KEY_BPM_PYTHON` to that venv.

## Architecture

Python is the analysis engine. C++ is a thin, tested CLI/process layer. Native C++
DSP is out of scope for v0.x.

## License

MIT for first-party code — see [LICENSE](LICENSE). Runtime wheels have their own
licenses — see [THIRD_PARTY.md](THIRD_PARTY.md).
