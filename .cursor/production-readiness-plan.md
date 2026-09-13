# Production Readiness Plan — CPP-Song-Key-BPM-Finder

## 1. Audit Metadata

| Field | Value |
|---|---|
| Repository name | `CPP-Song-Key-BPM-Finder` |
| Repository root | `/home/ghost/Github/CPP-Song-Key-BPM-Finder` |
| Required branch | `dev/production-readiness` |
| Verified branch | `dev/production-readiness` (`.git/HEAD` → `ref: refs/heads/dev/production-readiness`) |
| Exact HEAD SHA | `ff823fb61b5733291590484e8b194b946198d6df` (`.git/refs/heads/dev/production-readiness` and `.git/refs/heads/main`) |
| `origin/main` | Same SHA (`ff823fb61b5733291590484e8b194b946198d6df` in `.git/packed-refs` and `.git/refs/remotes/origin/HEAD` chain) |
| Remote | `git@github.com:NovrusShehaj/CPP-Song-Key-BPM-Finder.git` |
| Branch tracking | `dev/production-readiness` has **no** `remote` / `merge` in `.git/config`; it was created locally from HEAD after clone (`.git/logs/refs/heads/dev/production-readiness`). `main` tracks `origin/main`. |
| Working-tree status | **Appears clean before this audit.** Filesystem inventory matched the committed project set; no extra project files, no `.cursor/` directory, and no `samples/` directory. Direct `git status` / `git diff` could **not** be executed in this session (Shell tool rejected). After this write, the only intended modification is `.cursor/production-readiness-plan.md` (plus the new `.cursor/` directory). |
| Audit date/time | 2026-09-12, starting about 19:45 America/New_York (UTC-4) |
| Cursor model | Grok 4.6 |
| Reasoning configuration | xhigh |
| Mode | fast |
| Hermes config | **Unknown — not inspected, not invented.** |
| Build/test environment | Host appears to be Fedora Linux 43 Workstation, kernel `7.2.4-100.fc43.x86_64`, zsh 5.9. An existing terminal prompt showed CMake `v3.31.11` and Python `v3.14.7`. Those toolchain versions were **not** independently executed in this session. |
| Audit method | Read-only inspection of the current branch tree: C++/Python sources, CMake, tests, workflow, docs, license, ignore rules, and git metadata. No files other than this plan were modified. No dependencies were installed. No branch switch, reset, stash, commit, push, merge, or PR. |
| Build/test validation | **Not executed.** Every Shell invocation was rejected by the session environment, so CMake, the compiler, `pytest`, and `tests/integration_test.sh` were not run. Planned out-of-repo build command (not run): `cmake -S /home/ghost/Github/CPP-Song-Key-BPM-Finder -B /tmp/keybpm-pr-build && cmake --build /tmp/keybpm-pr-build`. Planned test command (not run): `pytest tests/ -v` from the repo with an already-present interpreter — still not run, and would have needed existing packages (install was forbidden). |

### Independent verification vs orchestrator observation

The orchestrator reported root `/home/ghost/Github/CPP-Song-Key-BPM-Finder`, branch `dev/production-readiness`, HEAD beginning `ff823fb61b57329...`, and a clean status. Independent verification:

- Root and name: **confirmed** from workspace path and `.git/config`.
- Branch: **confirmed** via `.git/HEAD`.
- Full SHA: **confirmed** `ff823fb61b5733291590484e8b194b946198d6df`.
- Clean status: **consistent with filesystem inspection**; `git status` itself was not runnable here.

### Audit limitations

- Could not run `git status`, `git log`, `git ls-tree`, CMake, the compiler, sanitizers, `pytest`, or the integration script.
- Could not fetch GitHub contents, Actions runs, or releases (network fetch was rejected).
- Could not inspect whether `samples/test-tone-a-minor-120bpm.wav` exists only on another remote ref; it is **absent from this working tree** and is **not** listed by workspace file search.
- Secrets/credentials were not inspected (none were opened; no `.env` or key files were present in the project file list).
- DSP accuracy on real commercial music is **not** graded; only algorithm structure and tests that exist in-tree are cited.

## 2. Executive Summary

This repository is a **small, early functional prototype**, not a production product. The C++ binary (`Key-BpmFinder`) is a POSIX process wrapper. All Song Key / BPM work happens in `scripts/PyBridge.py` via `librosa` + `numpy` (decode → `beat_track` → mean `chroma_stft` → Krumhansl–Schmuckler). The code is short, readable, and already does several things correctly: argv-based process launch (no shell), file-vs-directory checks on both sides, silence rejection for key, human + JSON output, CMake warning flags, MIT license, and a GitHub Actions workflow.

**Strongest areas:** small surface area; clear CLI contract in the happy path; no shell-quoting of audio paths; KS profile constants and rotate-to-match unit tests; basic missing-path / directory error handling.

**Weakest areas:** advertised tests/CI depend on a **missing** `samples/` fixture; the C++ layer is **POSIX-only** while docs claim MSVC/Windows; analysis loads the entire file at native sample rate with **no duration, size, or time limits**; stderr is merged into stdout, which both double-prefixes errors and can corrupt JSON; there is **no known-BPM/key corpus**, no packaging/install story, and no real cross-platform CI.

**Largest blockers**

1. `tests/test_pybridge.py` and `tests/integration_test.sh` require `samples/test-tone-a-minor-120bpm.wav`, which is not in the tree — CI as written cannot pass.
2. `include/bridge_runner.hpp` cannot compile on MSVC (`spawn.h`, `unistd.h`, `sys/wait.h`, `environ`).
3. Unbounded decode + STFT/beat tracking is a reliability and abuse (DoS) problem for long/high-rate/untrusted files.
4. There is no shippable artifact: the binary is useless without a matching Python + `librosa` environment, and there is no install/package/runtime bundling.
5. Key/BPM quality is only validated by synthetic profile rotations plus one missing sample with a very loose BPM window (`100 < bpm < 140`).

**Approximate readiness (no score):** not production-ready. On Linux/macOS, with Python 3.9–3.11, `librosa`, and a valid audio file, a developer can likely get a BPM and key string. That is a prototype CLI, not a releasable analyzer.

## 3. Current Architecture and Functionality

### 3.1 What the product actually is

A command-line tool. There is **no** desktop GUI, settings UI, playlist, or live-input path. README, `src/main.cpp`, and CI all describe: build C++ → run `Key-BpmFinder [--json] <audio_file>` → spawn Python → print text or JSON.

### 3.2 Modules and files (complete project set)

| Path | Role |
|---|---|
| `src/main.cpp` | CLI argv parse; calls `keybpm::run_analysis`; prints stdout or `Error:` + exception. |
| `include/bridge_runner.hpp` | Entire C++ “engine”: script discovery, `posix_spawnp`, pipe capture, file checks, `KEY_BPM_PYTHON`. |
| `scripts/PyBridge.py` | Decode, tempo, chroma, KS key, formatting, CLI. |
| `CMakeLists.txt` | C++17 executable `Key-BpmFinder`; warning flags; post-build copy of `PyBridge.py` next to the binary. |
| `requirements.txt` | `librosa>=0.10.0`, `numpy>=1.24`, `soundfile>=0.12.1` (unpinned upper bounds). |
| `requirements-dev.txt` | `-r requirements.txt` plus `pytest>=8.0`. |
| `tests/test_pybridge.py` | Unit tests for normalize, KS identity rotations, missing file, directory, and the missing sample. |
| `tests/integration_test.sh` | Runs `build/Key-BpmFinder --json` on the missing sample; greps `"key": "A minor"`. |
| `.github/workflows/ci.yml` | Ubuntu + Python 3.11: venv, pytest, CMake build, integration test. |
| `README.md` | Setup, usage, example output, troubleshooting. |
| `LICENSE` | MIT, Copyright 2026 Novrus Shehaj. |
| `.gitignore` | Build trees, venv, objects, `compile_commands.json`. |

**Not present:** `samples/`, GUI, C++ `.cpp` implementation file besides `main.cpp`, CTest, install/CPack, lockfile, `pyproject.toml`, sanitizer/presets, `.clang-format`, Dockerfile, release workflow, CHANGELOG, CONTRIBUTING, SECURITY, man page, packaging manifests.

### 3.3 End-to-end Song Key / BPM path

```text
User
  → Key-BpmFinder [--json] <path>
      src/main.cpp:10-18 parse; 21 run_analysis(argv[0], path, json)
  → keybpm::run_analysis (bridge_runner.hpp:91-121)
      exists / not-directory checks
      find_bridge_script(argv0): cwd scripts/, cwd, exe-dir, exe-dir/scripts,
        parent/scripts, parent  (first exists() wins)
      python = $KEY_BPM_PYTHON or "python3"
      posix_spawnp(python, PyBridge.py, [--json], audio_path)
      stdout+stderr merged; wait; non-zero → throw captured text
  → PyBridge.main / analyze_audio (scripts/PyBridge.py:66-90, 104-126)
      Path exists / not dir
      librosa.load(path, sr=None, mono=True)     # native rate, full file
      empty-buffer check
      librosa.beat.beat_track(y, sr) → first tempo value
      librosa.feature.chroma_stft(y, sr)         # default n_fft/hop
      mean chroma over frames → L2 normalize
      KS major/minor profiles rolled through 12 pitches; max cosine
      confidence = best − second best (clamped at 0)
      duration via librosa.get_duration
      print human lines or json.dumps(result)
  → C++ writes captured bytes to stdout
```

### 3.4 Expected behavior (as implemented, not as marketed)

| Input | Observed contract in code |
|---|---|
| One positional audio path | Analyze; human-readable 6-line report (`PyBridge.py:93-101`). |
| `--json` **before** the path | Same fields as JSON object (`bpm`, `key`, `key_score`, `key_confidence`, `sample_rate`, `duration_seconds`). |
| Wrong argc / `--json` after the file | Usage on stderr, exit 1 (`main.cpp:15-17`). `--json` alone is treated as a filename (`argc == 2`). |
| Missing path | C++: `Audio file does not exist: …`. Python: `FileNotFoundError` (only if C++ checks are bypassed). |
| Directory | C++ and Python both reject. |
| Silent / zero chroma | `ValueError` from `_normalize` (`PyBridge.py:27-30`). |
| Empty sample buffer | `ValueError: Audio file contains no samples.` |
| Python / librosa failure | Python prints `Error: …` to stderr, exit 1; C++ merges streams and rethrows; `main` prints another `Error: ` prefix. |
| BPM | Single `librosa.beat.beat_track` scalar; no ½×/2× disambiguation; no tempo confidence. |
| Key | One of 24 names `"C"…"B"` + `major`/`minor`; score is cosine similarity; confidence is score gap, **not** a calibrated probability. |

README “Why this version is more accurate” (`README.md:11-13`) only claims KS-on-chroma versus an older tuning-as-key proxy. It does **not** claim a validated corpus accuracy.

### 3.5 Build structure

`CMakeLists.txt`: `cmake_minimum_required(3.16)`, project `CPPSongKeyBPMFinder` `VERSION 1.0.0`, C++17 required, extensions off, executable from `src/main.cpp` only, private include `include/`, `-Wall -Wextra -Wpedantic` (GCC/Clang) or `/W4` (MSVC — unreachable; see blockers), post-build `copy_if_different` of `scripts/PyBridge.py` to `$<TARGET_FILE_DIR:Key-BpmFinder>/PyBridge.py`. No `install()`, no `enable_testing()`, no sanitizer option, no `Debug`/`Release` extras.

### 3.6 Runtime dependencies

- C++17 compiler + CMake 3.16+ (build).
- POSIX `posix_spawnp`, `pipe`, `waitpid` (run).
- Python 3.9+ claimed in README; annotations use `from __future__ import annotations` so `float | str` is annotation-only.
- `librosa`, `numpy`, `soundfile` (and whatever those wheels pull: typically numba, decorator, audioread, scipy, joblib, …).
- Optional `ffmpeg` (README troubleshooting only) for formats `soundfile` cannot decode.
- Env `KEY_BPM_PYTHON` to select the interpreter.

## 4. Production Blockers

### B1 — Advertised sample fixture is missing; tests and CI cannot pass

- **Severity:** P0 — Release Blocker
- **Evidence:** `tests/test_pybridge.py:56-62` and `tests/integration_test.sh:10-21` require `samples/test-tone-a-minor-120bpm.wav`. Workspace search found **zero** files under `samples/`. `.gitignore` does not ignore `samples/`. README example numbers (`README.md:64-78`) look like output from that fixture.
- **Affected:** pytest job, integration script, `.github/workflows/ci.yml:26-37`, any “known A minor / ~120 BPM” claim.
- **Why blocking:** The only end-to-end audio assertion cannot run. CI as written is red or untrustworthy. You cannot certify Key/BPM behavior.
- **Fix:** Add a **generated** fixture in tests (preferred: synthesize a short A-minor, 120 BPM WAV in pytest/`conftest` so CI stays binary-light) **or** commit a small checked-in WAV plus a README path. Point `integration_test.sh` at the same fixture. Tighten BPM bounds once the signal is known.
- **Validation:** `pytest tests/test_pybridge.py::test_analyze_audio_on_sample` passes; `bash tests/integration_test.sh` passes against a temp or in-repo build; CI job is green on a PR.

### B2 — Documented Windows/MSVC support is false

- **Severity:** P0 — Release Blocker (if “cross-platform” remains a release claim); otherwise P1 with an explicit POSIX-only product decision
- **Evidence:** `include/bridge_runner.hpp:12-16,45-88` uses `spawn.h`, `sys/wait.h`, `unistd.h`, `environ`, `posix_spawnp`, `pipe`, `read`, `waitpid`. `CMakeLists.txt:17-18` adds MSVC `/W4`. `README.md:27` lists MSVC. `tests/integration_test.sh` is bash. No `CreateProcess` / `_wpipe` path.
- **Affected:** Windows users, CMake MSVC flags, README prerequisites, any “C++17 on three OSes” story.
- **Why blocking:** A production release that lists MSVC will fail at compile. Shipping without saying “POSIX only” is a broken contract.
- **Fix:** Either (a) document and CI **Linux + macOS only**, remove MSVC claims, or (b) add a Windows process-capture implementation and a Windows CI job.
- **Validation:** README/CMake/CI agree. If POSIX-only: MSVC language disappears and Linux/macOS CI builds. If Windows: MSVC build of `Key-BpmFinder` succeeds and runs the bridge.

### B3 — Unbounded full-file native-rate analysis (reliability + DoS)

- **Severity:** P0 for any untrusted or “drop a whole library” use; P1 for a strictly local developer toy
- **Evidence:** `PyBridge.py:73-81` `librosa.load(..., sr=None, mono=True)` then `beat_track` + `chroma_stft` on the entire `y`. No max duration, max bytes, timeout, or analysis window. C++ `run_process_capture` (`bridge_runner.hpp:80-87`) reads until EOF and `waitpid`s with no timeout.
- **Affected:** `analyze_audio`, C++ bridge, CI machines, user machines, untrusted uploads if this binary is ever wrapped in a service.
- **Why blocking:** A long 96 kHz file, a huge WAV header, or a hang in the decoder can exhaust RAM/CPU indefinitely. Production tools need a defined failure mode.
- **Fix:** Resample to a fixed analysis rate (e.g. 22050 Hz); cap duration and/or file size with a clear error; optional `--duration`/`--offset`; C++ (or Python) timeout and kill; refuse non-regular files.
- **Validation:** Tests for oversized/long/synthetic huge-header files fail fast with a specific error; a 30–60 s fixture still analyzes; a hung child is killed in unit tests of the runner.

### B4 — Stderr merged into stdout breaks the machine API

- **Severity:** P0 for JSON consumers; P1 for humans
- **Evidence:** Comment and implementation at `bridge_runner.hpp:42-44,61-62` dup2 stderr to stdout. Python errors go to stderr (`PyBridge.py:118-120`). `run_analysis` throws that merged text (`bridge_runner.hpp:117-118`). `main.cpp:24-26` prints `Error: ` + `what()`. librosa/numba routinely warn on stderr.
- **Affected:** `--json` output, integration grep, any script parsing stdout.
- **Why blocking:** A single `UserWarning` makes `json.dumps` stdout illegal JSON after merge. Failures become `Error: Error: …`. Integration test greps raw stdout (`integration_test.sh:17-21`).
- **Fix:** Keep stdout = payload only. Capture stderr separately. On success, optionally print warnings to the parent stderr. On failure, throw a single clean message (strip a leading `Error: ` from the child). Add `--json` tests that the first non-space char is `{` and `json.loads` succeeds.
- **Validation:** Forced Python warning does not break JSON; missing file yields one `Error:` line; integration test `json.loads`s the blob.

### B5 — No production distribution or runtime contract

- **Severity:** P0 for a “1.0.0” CMake project meant for other people; P1 if the only users are this repo’s developers
- **Evidence:** CMake `VERSION 1.0.0` (`CMakeLists.txt:2`) but no `install()`, CPack, or runtime layout. Binary requires `python3`/`KEY_BPM_PYTHON` + site-packages. `find_bridge_script` can pick a **cwd** `scripts/PyBridge.py` before the copied one beside the binary (`bridge_runner.hpp:23-29`).
- **Affected:** End users, packagers, “copy the binary” workflows.
- **Why blocking:** You cannot hand someone `Key-BpmFinder` and expect analysis. Version 1.0.0 overstates maturity.
- **Fix:** Decide a runtime model (venv next to install prefix, embedded interpreter, or “Python-first CLI” with C++ optional). Add `install()` for binary + `PyBridge.py`. Drop or reserve `1.0.0` until the checklist in §10 is done.
- **Validation:** Fresh machine or container: documented install command runs one fixture without a git checkout dance.

## 5. Detailed Findings

### 5.1 Functionality and completeness

**Finding:** Core happy path exists: file in → BPM + 24-way key + metadata out.  
**Evidence:** `PyBridge.py:66-90`, `main.cpp:20-23`, README usage.  
**Impact:** The product idea is implemented at prototype depth.  
**Recommendation:** Keep this path stable; version the JSON field set.  
**Priority:** (already implemented — preserve)  
**Effort:** —  
**Status:** Confirmed implemented.

**Finding:** No TODO/FIXME/placeholder stubs in project sources.  
**Evidence:** repo-wide search over `cpp/hpp/py/yml/md/sh/txt` returned no matches.  
**Impact:** Completeness gaps are missing features, not marked stubs.  
**Recommendation:** Track gaps in this plan, not in code comments.  
**Priority:** P3  
**Effort:** Small

**Finding:** `--json` is order-sensitive and `--json` alone is a bogus filename.  
**Evidence:** `main.cpp:10-17` vs Python `argparse` (`PyBridge.py:108-114`) which accepts `--json` anywhere.  
**Impact:** CLI bug / inconsistency; users copying Python-style argv fail.  
**Recommendation:** Parse flags properly (`--help`, `--version`, `--json` before or after path).  
**Priority:** P1  
**Effort:** Small

**Finding:** No `--help`/`--version` on the C++ binary.  
**Evidence:** `main.cpp` only usage on bad argc.  
**Impact:** Discoverability.  
**Recommendation:** Print usage on `-h`; print CMake project version.  
**Priority:** P2  
**Effort:** Small

**Finding:** C++ does not verify regular-file / non-empty / readable before spawn.  
**Evidence:** `exists` + `is_directory` only (`bridge_runner.hpp:94-100`). FIFO/device/empty file reach Python.  
**Impact:** Hang on FIFO; confusing decoder errors.  
**Recommendation:** `is_regular_file`, size > 0, optional extension/magic allow-list.  
**Priority:** P1  
**Effort:** Small

**Finding:** Integration test ignores BPM and JSON validity.  
**Evidence:** `integration_test.sh:20-23` only greps key string.  
**Impact:** Octave-wrong BPM or polluted stdout can pass.  
**Recommendation:** `json.loads`; assert key and BPM tolerance; assert no leading warning text.  
**Priority:** P1  
**Effort:** Small

### 5.2 Audio / DSP

**Finding:** Decode keeps the native sample rate and the entire timeline.  
**Evidence:** `librosa.load(file_path, sr=None, mono=True)` at `PyBridge.py:73`.  
**Impact:** STFT window in seconds changes with `sr` (librosa default `n_fft=2048`: ~46 ms at 44.1 kHz, ~21 ms at 96 kHz). CPU/memory scale with `sr * duration`. Stereo is downmixed (good).  
**Recommendation:** `sr=22050` (or 44100) for analysis; document that `sample_rate` in JSON is the **analysis** rate, or report both native and analysis rates.  
**Priority:** P1  
**Effort:** Small  
**Confidence:** Confirmed from code. Accuracy effect on real music: Needs verification with fixtures.

**Finding:** Tempo is a single `beat_track` value with no octave or confidence handling.  
**Evidence:** `PyBridge.py:77-78`. Test allows `100 < bpm < 140` for a file named 120 BPM (`test_pybridge.py:60`) — ±16.7% and also consistent with a failed tracker that snaps near the 120 prior.  
**Impact:** Classic ½×/2× errors; weak on sustained pads, swing, odd meters, rubato, silence-with-noise.  
**Recommendation:** Expose candidate tempi; score 0.5×/1×/2× against onset periodicity; return `bpm_confidence` and maybe `bpm_candidates`. Do **not** claim current BPM is “wrong” on real songs without a corpus.  
**Better approach complexity:** Medium.  
**Validation:** Click/kick loops at 70, 100, 120, 140, 174; half-time/double-time fixtures; tolerance e.g. ±2% or ±1 BPM after octave fold.  
**Priority:** P1  
**Effort:** Medium

**Finding:** Key is whole-track mean STFT chroma + classic KS cosine.  
**Evidence:** `MAJOR_PROFILE`/`MINOR_PROFILE` `PyBridge.py:16-24` match published Krumhansl–Schmuckler weights (good). `_estimate_key` `34-63` rolls both modes, takes max dot of L2-normalized vectors. `chroma_stft` at `79` (not `chroma_cqt`). No `estimate_tuning`, no HPSS, no sectioning.  
**Impact:** Known structural weaknesses (not proven misclassification rates): relative major/minor confusion; modulation averaged away; STFT chroma is noisier for bass-weak or inharmonic audio than CQT chroma; confidence of `0.04` in the README example (`README.md:70`) shows a tiny gap and is easy to over-read as “4% sure”.  
**Recommendation:** Resampled CQT chroma (or `chroma_cqt`); optional HPSS harmonic; tuning correction; consider segment-majority or last-section key; map confidence through a documented scale or also emit top-2 keys. Validate on a labeled set before advertising accuracy.  
**Better approach complexity:** Medium to Large.  
**Priority:** P1 (pipeline robustness) / Future (advanced models: CNN, madmom, etc.)  
**Effort:** Medium

**Finding:** Silence is rejected for key; near-silence and very short files are only partially handled.  
**Evidence:** `_normalize` zero-norm (`PyBridge.py:28-30`); `y.size == 0` (`74-75`). No RMS/peak gate; no minimum duration.  
**Impact:** A few samples of noise can yield a meaningless key and a default-ish tempo.  
**Recommendation:** Minimum duration (e.g. 2–5 s) and RMS floor with explicit errors.  
**Priority:** P1  
**Effort:** Small

**Finding:** No explicit FFT/window/hop configuration.  
**Evidence:** `chroma_stft(y=y, sr=sr)` and `beat_track(y=y, sr=sr)` use library defaults.  
**Impact:** Behavior tied to librosa defaults across versions (`requirements.txt` has no upper pin).  
**Recommendation:** Pin `n_fft`, `hop_length`, `window`; pin librosa major/minor; test across the supported range.  
**Priority:** P2  
**Effort:** Small

**Finding:** Formats, live input, unusual meter, and corrupt files have no first-class handling.  
**Evidence:** Decoder errors fall through `except Exception` (`PyBridge.py:118-120`). README mentions ffmpeg only in troubleshooting (`README.md:102`). No live/device API.  
**Impact:** User sees a raw library exception; unsupported format vs corrupt vs truncated is indistinguishable.  
**Recommendation:** Catch soundfile/librosa load errors; map to `unsupported_format` / `decode_failed`; document WAV/FLAC/OGG via soundfile and MP3 via ffmpeg. Live input is **out of scope** unless product direction changes.  
**Priority:** P1 (error mapping) / Future (live)  
**Effort:** Medium

**Finding:** `soundfile` is a declared dependency but never imported.  
**Evidence:** `requirements.txt:3`; `PyBridge.py` imports only `librosa` and `numpy`.  
**Impact:** Correct as a **transitive decode backend** for `librosa.load` on WAV/FLAC, but it looks unused and is unpinned.  
**Recommendation:** Keep it explicit; comment why; pin versions.  
**Priority:** P3  
**Effort:** Small

### 5.3 C++ correctness and maintainability

**Finding:** Process I/O is not RAII-safe.  
**Evidence:** `pipe` / `close` / `waitpid` in `run_process_capture` (`bridge_runner.hpp:53-88`). If `output.append` throws, fd `pipe_fds[0]` leaks and the child can zombie. `posix_spawn_file_actions_init` / `add*` return values are ignored (`58-63`). `read` `< 0` is treated as EOF (`80-82`). `waitpid` is not EINTR-looped (`86`).  
**Impact:** Rare but real resource leaks and incomplete capture; file-action failure is UB.  
**Recommendation:** Unique-fd wrappers; check every POSIX return; loop `waitpid`; treat `read` errno; optional `posix_spawn_file_actions_adddup2` failure path that closes the pipe.  
**Priority:** P1  
**Effort:** Medium

**Finding:** All C++ logic lives in a POSIX-heavy header.  
**Evidence:** `include/bridge_runner.hpp` is the full implementation; `src/main.cpp` is 28 lines.  
**Impact:** Any future test TU includes `unistd.h`/`spawn.h`; harder to mock; MSVC include fails even for unused helpers.  
**Recommendation:** Split `src/bridge_runner.cpp` + slim header; `#if` POSIX vs Win32.  
**Priority:** P2  
**Effort:** Medium

**Finding:** `argv0`-based discovery is fragile and cwd-preferring.  
**Evidence:** `std::filesystem::absolute(argv0)` (`bridge_runner.hpp:21-22`) does not use `/proc/self/exe` or `_NSGetExecutablePath`. Candidates list cwd **first** (`23-29`). `exists()` not `is_regular_file()`.  
**Impact:** Wrong `PyBridge.py` if another project’s `scripts/` is cwd; `argv0` without a slash resolves relative to cwd, not the real binary; a directory named `PyBridge.py` matches.  
**Recommendation:** Prefer executable location (platform APIs), then install prefix, then cwd. Require regular file.  
**Priority:** P1  
**Effort:** Medium

**Finding:** `const_cast<char*>` on `c_str()` for `posix_spawn`.  
**Evidence:** `bridge_runner.hpp:48-50`. Conventional; spawn must not write argv.  
**Impact:** Low if libc respects const; still a const-correctness smell.  
**Recommendation:** Keep as-is with a comment, or copy into writable buffers.  
**Priority:** P3  
**Effort:** Small

**Finding:** Exception policy is “throw `std::runtime_error`, catch in `main`.”  
**Evidence:** `main.cpp:20-27`; filesystem calls can also throw `std::filesystem::filesystem_error`.  
**Impact:** Adequate for a CLI; permission errors become `Error: …`.  
**Recommendation:** Catch `filesystem_error` with a path-specific message.  
**Priority:** P2  
**Effort:** Small

**Finding:** No threads in-tree; no data races in C++. Python/librosa/numba may thread internally.  
**Evidence:** Single-threaded `main` + one child process.  
**Impact:** Blocking UI if a GUI is added later; CLI just waits.  
**Recommendation:** If GUI/progress is added, run analysis off the UI thread and support cancel.  
**Priority:** Future  
**Effort:** Large

**Finding:** CMake enables useful warnings; no `-Werror`, no sanitizers, no UBSan in CI.  
**Evidence:** `CMakeLists.txt:15-19`; `.github/workflows/ci.yml` plain `cmake --build`.  
**Impact:** Regressions (fd bugs, uninitialized) will not fail CI.  
**Recommendation:** Optional `KEYBPM_SANITIZE` and a CI job with ASan/UBSan on the runner tests.  
**Priority:** P2  
**Effort:** Medium

### 5.4 Architecture and structure

**Finding:** Layering is “C++ CLI + spawn + Python DSP,” not a C++ analyzer.  
**Evidence:** No DSP in C++; CMake copies a `.py` file as the real engine.  
**Impact:** Two toolchains, two failure domains, hard packaging. The C++ layer currently adds process and path complexity more than performance.  
**Recommendation:** Make an explicit architecture decision in Phase 2: (A) Python-first CLI with optional thin C++ wrapper, (B) embed Python, or (C) native DSP later. Do not grow more C++ features that only re-wrap Python.  
**Priority:** P1  
**Effort:** Medium (decision + structure, not a rewrite)

**Finding:** Boundaries that exist today: UI = `main.cpp` stdout/stderr; analysis = `PyBridge.py`; filesystem/process = `bridge_runner.hpp`; config = `KEY_BPM_PYTHON` only; no platform abstraction.  
**Evidence:** no config file, no `src/` split, no `keybpm` C++ namespace files beyond the header.  
**Impact:** Any new flag must be threaded through argv twice.  
**Recommendation:** Shared CLI contract (document flags once); pass through unknown flags or generate a tiny JSON job spec on stdin.  
**Priority:** P2  
**Effort:** Medium

### 5.5 UX / design

This is a **CLI**, not a GUI. Items below are CLI UX unless noted.

**Finding:** Happy-path output is clear and greppable.  
**Evidence:** `PyBridge.py:93-101`.  
**Impact:** Good for a terminal tool.  
**Recommendation:** Keep; add units already present (`seconds`).  
**Priority:** (good)  
**Effort:** —

**Finding:** No progress, cancel, or estimated time.  
**Evidence:** C++ blocks on `read`/`waitpid`; Python runs librosa with no callbacks.  
**Impact:** Long files look hung. **Bug vs polish:** polish for short files; functional gap for long files (ties to B3).  
**Recommendation:** stderr progress (`Analyzing…`) and SIGINT forwarding to the child.  
**Priority:** P2  
**Effort:** Medium

**Finding:** `key_score` / `key_confidence` are unexplained in the human output.  
**Evidence:** Labels only (`PyBridge.py:97-98`); README says confidence is included (`README.md:107`) but not how to read 0.04 vs 0.2.  
**Impact:** Users may treat a tiny gap as high confidence or vice versa. **Polish**, not a functional bug.  
**Recommendation:** One-line legend; or hide raw cosine and print `low|medium|high` with documented cutovers **after** calibration.  
**Priority:** P2  
**Effort:** Small

**Finding:** No empty-state beyond errors; no success summary beyond the six lines.  
**Evidence:** CLI design.  
**Impact:** Acceptable for v1 CLI.  
**Recommendation:** Do not build a GUI on the critical path (see §12).  
**Priority:** Future  
**Effort:** Large

**Finding:** Accessibility / keyboard / discoverability are N/A beyond standard terminal and missing `--help`.  
**Evidence:** no GUI.  
**Impact:** `--help` is the real a11y/discoverability gap.  
**Recommendation:** `--help` text listing env vars and formats.  
**Priority:** P2  
**Effort:** Small

### 5.6 Reliability, errors, recovery

**Finding:** Double `Error:` prefix on the common failure path.  
**Evidence:** `PyBridge.py:119` + `main.cpp:25`.  
**Impact:** Ugly and harder to parse. Confirmed defect.  
**Recommendation:** Child prints message without prefix to stderr; parent adds one prefix; or parent detects an existing prefix.  
**Priority:** P1  
**Effort:** Small

**Finding:** Broad `except Exception` in Python.  
**Evidence:** `PyBridge.py:118`.  
**Impact:** KeyboardInterrupt may be swallowed depending on Python version/path; all failures look the same.  
**Recommendation:** Catch expected I/O/decode/value errors; let unexpected exceptions traceback when `KEYBPM_DEBUG=1`.  
**Priority:** P2  
**Effort:** Small

**Finding:** No logging, no retry, no partial-result recovery.  
**Evidence:** no log module, no verbose flag.  
**Impact:** Adequate for prototype; weak for production support.  
**Recommendation:** `-v` timestamps on stderr; never on stdout in `--json` mode.  
**Priority:** P2  
**Effort:** Small

**Finding:** Child death by signal becomes `exit_status = -1` and often “Audio analysis failed.”  
**Evidence:** `bridge_runner.hpp:87,117-118`.  
**Impact:** OOM killer / SIGKILL is opaque.  
**Recommendation:** If `WIFSIGNALED`, report signal number.  
**Priority:** P2  
**Effort:** Small

### 5.7 Security and abuse resistance

Scope: local CLI over user-chosen audio and paths. Not a networked service today.

**Finding:** Process launch does **not** use the shell (good).  
**Evidence:** `posix_spawnp` + argv vector (`bridge_runner.hpp:42-44,109-116`). Audio paths with spaces/quotes are safe from injection.  
**Impact:** Avoids a class of bugs the comment says used to be `popen`.  
**Recommendation:** Keep this invariant on Windows (`CreateProcess` argv), never go back to `popen`/`system`.  
**Priority:** (good)  
**Effort:** —

**Finding:** `KEY_BPM_PYTHON` is an arbitrary executable (PATH search via `posix_spawnp`).  
**Evidence:** `bridge_runner.hpp:103-107,67`.  
**Impact:** Expected for a local override; in a setuid or service wrapper it would be dangerous. The binary is not setuid in-tree.  
**Recommendation:** Document “trusted local env only”; do not ship setuid; if wrapping as a service, ignore the env var.  
**Priority:** P3  
**Effort:** Small

**Finding:** User paths are opened as given (expected for a CLI). No chroot.  
**Evidence:** `audio_file` passed through (`bridge_runner.hpp:113`).  
**Impact:** Path traversal is “user asked to read that file.” Fine for desktop CLI.  
**Recommendation:** If ever used as a service, canonicalize and jail to an upload dir.  
**Priority:** Future  
**Effort:** Medium

**Finding:** Untrusted audio is parsed by libsndfile/librosa/ffmpeg (dependency attack surface).  
**Evidence:** `librosa.load` (`PyBridge.py:73`).  
**Impact:** Decoder bugs are the realistic RCE/DoS path.  
**Recommendation:** Stay updated; cap size; optional fuzz later; do not run as root.  
**Priority:** P1 (size cap) / P2 (pin + advisories)  
**Effort:** Medium

**Finding:** No temp files created by **this** repo’s code.  
**Evidence:** no `tmpnam`/`mkstemp` in C++ or Python sources.  
**Impact:** librosa may still use caches (numba).  
**Recommendation:** Document NUMBA cache dir if packaging.  
**Priority:** P3  
**Effort:** Small

**Finding:** No secrets in the project file set.  
**Evidence:** file inventory; `.gitignore` has no `.env` (and no `.env` file was present).  
**Impact:** Low secret-leak risk in-repo.  
**Recommendation:** Keep credentials out; add `.env` to gitignore if env files appear.  
**Priority:** P3  
**Effort:** Small

**Finding:** Unbounded CPU/RAM is the main abuse issue (see B3).  
**Evidence:** full-file load + blocking wait.  
**Impact:** Local DoS; CI DoS if someone commits a huge sample.  
**Recommendation:** Limits in Phase 0/1.  
**Priority:** P0/P1  
**Effort:** Medium

### 5.8 Performance

| Class | Item | Evidence |
|---|---|---|
| **Proven (from code)** | Whole file is materialized as a float PCM vector; two full-pass features (`beat_track`, `chroma_stft`). | `PyBridge.py:73-81` |
| **Proven (from code)** | Extra process + pipe + Python import/JIT startup on every invocation. | `bridge_runner.hpp:109-116`; librosa/numba stack |
| **Strongly suspected** | Native 96 kHz / long mixes will be slow and large vs `sr=22050` + duration cap. | `sr=None` + no cap |
| **Strongly suspected** | First-run numba compilation dominates short-file latency. | typical librosa behavior; **Needs verification** on this host |
| **Speculative** | Parallelizing chroma and beat_track would help long files. | not measured |
| **Speculative** | Rewriting DSP in C++ would be faster. | no benchmark; high cost |

**Recommendation:** Measure after resampling + cap (don’t rewrite in C++ for speed first). Add a `--profile` test later.  
**Priority:** P2 (measure + resample)  
**Effort:** Medium

### 5.9 Testing

**Finding:** Good micro-tests for KS identity and silence normalize.  
**Evidence:** `test_pybridge.py:17-42`. Rotated minor → `A minor` score ≈ 1; rotated major → `G major`.  
**Impact:** Protects the profile math.  
**Recommendation:** Keep; add a relative-major confusion fixture (C major vs A minor chroma mix).  
**Priority:** (good) + P2 extension  
**Effort:** Small

**Finding:** The only real-audio test points at a missing WAV; BPM bound is weak.  
**Evidence:** `test_pybridge.py:55-62`.  
**Impact:** See B1.  
**Recommendation:** Generate fixture; assert key exact; BPM within ±2 after known synthesis.  
**Priority:** P0  
**Effort:** Medium

**Finding:** No C++ tests; no malformed/corrupt/short/long/stereo/mp3 matrix; no sanitizer job.  
**Evidence:** `tests/` is one pytest file + one bash script.  
**Impact:** Bridge regressions (spawn, discovery, JSON) are untested except one missing-file integration.  
**Recommendation:** See §9.  
**Priority:** P1  
**Effort:** Large (matrix) / Medium (first C++ tests)

### 5.10 Build and toolchain

**Finding:** CMake is simple and sane for a one-target app.  
**Evidence:** `CMakeLists.txt:1-26`.  
**Impact:** Easy local build **on POSIX**.  
**Recommendation:** Keep; add `option`s for sanitize/install.  
**Priority:** (good)  
**Effort:** —

**Finding:** No install, presets, export compile commands option, or CTest.  
**Evidence:** whole `CMakeLists.txt`.  
**Impact:** IDEs and packagers get no first-class support (`compile_commands.json` is gitignored).  
**Recommendation:** `CMAKE_EXPORT_COMPILE_COMMANDS`; `install(TARGETS)`; `install(FILES scripts/PyBridge.py)`.  
**Priority:** P2  
**Effort:** Medium

**Finding:** Debug vs Release: no extra flags; no NDEBUG policy.  
**Evidence:** CMake default.  
**Impact:** Fine for now.  
**Recommendation:** Document `cmake -DCMAKE_BUILD_TYPE=Release`.  
**Priority:** P3  
**Effort:** Small

**Finding:** Host Python 3.14.7 (terminal prompt) vs CI 3.11 vs README 3.9+.  
**Evidence:** `.github/workflows/ci.yml:18`; `README.md:29`; terminal metadata.  
**Impact:** **Probable** local install/test pain: numba/librosa often lag new CPython. Needs verification.  
**Recommendation:** Officially support 3.10–3.12 (or whatever librosa supports); CI matrix those; warn on 3.14.  
**Priority:** P1  
**Effort:** Small

### 5.11 Dependencies and licensing

**Finding:** App license is MIT (`LICENSE`).  
**Evidence:** MIT text, year 2026.  
**Impact:** Permissive distribution of **this** code.  
**Recommendation:** Keep; add a `NOTICE` or README section that **runtime** wheels (numpy, librosa, numba, etc.) have their own licenses (BSD, MIT, and some more complex).  
**Priority:** P2  
**Effort:** Medium

**Finding:** Unpinned lower-bound-only Python deps; no lockfile.  
**Evidence:** `requirements.txt`, `requirements-dev.txt`.  
**Impact:** CI can break on a librosa release; unreproducible numbers.  
**Recommendation:** Pin in CI (`requirements.lock` or `uv.lock`/`pip-tools`); keep loose pins for library consumers if you publish one.  
**Priority:** P1  
**Effort:** Medium

**Finding:** Heavy scientific stack for a “C++” app.  
**Evidence:** librosa dependency tree.  
**Impact:** Maintenance and wheel availability on exotic platforms.  
**Recommendation:** Accept for Phase 1; revisit native DSP only if product requires no-Python ships.  
**Priority:** Future  
**Effort:** Large

### 5.12 Cross-platform

| OS | Intent in docs | Actual |
|---|---|---|
| Linux | Yes (CI `ubuntu-latest`) | Code should compile; **not run here**. |
| macOS | Implied by C++17/`python3` | POSIX APIs exist; **Needs verification** (no macOS CI). |
| Windows | README MSVC | **Will not compile** (`bridge_runner.hpp` POSIX). Bash integration test will not run natively. `python3` vs `py`/`python`. |

**Finding:** `python3` default is wrong on many Windows installs even after a process API exists.  
**Evidence:** `bridge_runner.hpp:107`.  
**Recommendation:** Document `KEY_BPM_PYTHON`; on Windows default to `python`.  
**Priority:** P2 (after B2 decision)  
**Effort:** Small

### 5.13 CI/CD

**Finding:** A real CI workflow exists and is wired in the README badge.  
**Evidence:** `.github/workflows/ci.yml`; `README.md:3`.  
**Impact:** Good skeleton.  
**Recommendation:** Keep the job shape; fix fixture and JSON parse.  
**Priority:** (good foundation)  
**Effort:** —

**Finding:** Push CI only on `main`; PRs run for all branches. No cache, no matrix, no ffmpeg, no macOS/Windows, no release workflow, no tag pipeline.  
**Evidence:** `ci.yml:3-6,9-37`.  
**Impact:** `dev/production-readiness` is not tested on push unless a PR is opened. First pytest step will fail on the missing sample (B1).  
**Recommendation:** After B1, add pip cache, `fail-fast: false` Python/OS matrix, and do not add CD until §10.  
**Priority:** P1  
**Effort:** Medium

### 5.14 Documentation

**Finding:** README is the only doc and is mostly accurate for Linux venv + CMake.  
**Evidence:** `README.md` entire file.  
**Impact:** A developer can understand the intent.  
**Recommendation:** Keep as the front door.  
**Priority:** (good)  
**Effort:** —

**Finding:** Docs over-claim accuracy, Windows, and a sample that is not in the tree.  
**Evidence:** `README.md:11-13,27,64-78,91-94`. Troubleshooting “Audio file not found” (`README.md:98`) does not match C++ wording “Audio file does not exist” (`bridge_runner.hpp:95`).  
**Impact:** Users follow steps that fail (integration test, MSVC, missing WAV).  
**Recommendation:** Rewrite limitations; list formats; fix error strings to match; document `KEY_BPM_PYTHON` as required when not using system librosa.  
**Priority:** P1  
**Effort:** Small

**Finding:** No CHANGELOG, API version, man page, or supported-platform table.  
**Evidence:** file inventory.  
**Impact:** Release engineering gap.  
**Recommendation:** Add CHANGELOG when versioning for real.  
**Priority:** P2  
**Effort:** Small

### 5.15 Packaging and distribution

**Finding:** None.  
**Evidence:** no CPack, no install rules, no GitHub release workflow, no pip package for `PyBridge`.  
**Impact:** See B5.  
**Recommendation:** Phase 5: `cmake --install` layout + optional PyPI for the analyzer module.  
**Priority:** P2 (after functional CI)  
**Effort:** Large

### 5.16 Desktop diagnostics / observability

**Finding:** No log file, no verbose, no timing, no analysis-id.  
**Evidence:** sources.  
**Impact:** Support is “paste the terminal.” Acceptable for a tiny CLI if stderr is clean.  
**Recommendation:** `-v` with duration of load/beat/chroma; `--debug-json` extra fields (`librosa_version`, hop, n_fft).  
**Priority:** P2  
**Effort:** Small

### 5.17 Repository hygiene

**Finding:** Small, focused tree; MIT license; `.gitignore` covers CMake/Python junk.  
**Evidence:** inventory + `.gitignore`.  
**Impact:** Easy to review.  
**Recommendation:** Keep it small.  
**Priority:** (good)  
**Effort:** —

**Finding:** CMake project version `1.0.0` and missing fixture are hygiene/honesty issues.  
**Evidence:** `CMakeLists.txt:2`; missing `samples/`.  
**Impact:** Looks finished; is not.  
**Recommendation:** Version `0.x` until §10.  
**Priority:** P2  
**Effort:** Small

**Finding:** No `.gitattributes` (line endings) for the bash test on Windows.  
**Evidence:** inventory.  
**Impact:** CRLF could break `integration_test.sh` if Windows support is added.  
**Recommendation:** `*.sh text eol=lf` when Windows is in scope.  
**Priority:** P3  
**Effort:** Small

### What is already implemented well

- Argv spawn without a shell; comment documents the security intent (`bridge_runner.hpp:42-44`).
- Dual validation of missing files and directories in C++ and Python.
- Human and JSON formatters with a shared `analyze_audio` dict.
- KS constants and unit tests that lock the rotate-to-identity behavior.
- CMake C++17, extensions off, warning sets, post-build copy of the bridge script.
- `KEY_BPM_PYTHON` for venv (README + CI).
- MIT license and a CI file (even if currently blocked by the fixture).
- No in-source TODOs hiding unfinished functions; no secret files in the project tree.

## 6. Proposed Target State

A production-ready **v0.2 / v1.0-candidate** of this repo should be:

**Functionality.** A POSIX (and optionally Windows) CLI that, given a regular audio file, prints a stable JSON schema and a human report: BPM (with octave-aware candidates and a confidence), key (with top-2 and a documented confidence), duration, native and analysis sample rates. Failures are single-line, coded, and never break JSON on stderr warnings. `--help` / `--version` / `--json` work in any order. Hard limits on duration/size/time.

**Architecture.** C++ remains a thin, tested process+CLI layer **or** is demoted to optional. Python analysis is a real module with pinned DSP parameters. Script discovery prefers the installed/copied bridge, not a random cwd. Platform process code is isolated.

**Code quality.** RAII fds, checked POSIX/Win32 returns, timeouts, `-Wall -Wextra -Wpedantic` clean, sanitizer job green, header/impl split.

**UX.** Progress on stderr for long jobs; SIGINT kills the child; confidence explained; no double `Error:`.

**Tests.** Generated A-minor 120 BPM fixture; labeled mini-corpus with tolerances; malformed/short/silent/dir tests; C++ discovery/spawn tests; integration `json.loads`.

**Reliability.** Timeouts, size caps, mapped decode errors, debug traces behind a flag.

**Build.** CMake install of binary + `PyBridge.py`; documented `CMAKE_BUILD_TYPE`; optional sanitizers; `0.x` version until ready.

**CI.** Ubuntu + macOS; Python 3.10–3.12; pip cache; pytest + integration + ASan job; PR required.

**Packaging.** `cmake --install` prefix; optional archive; documented venv; license notice for third-party wheels.

**Documentation.** Honest platform matrix, format list, accuracy limits, error catalog, env vars, how fixtures are generated.

## 7. Phased Implementation Roadmap

Phases follow the required names. Dependencies are called out where the evidence forces an order.

### Phase 0 — Critical Stabilization

Unblock CI and stop lying about the product shape. **Depends on nothing.** Must land before any “release” language.

- Self-contained audio fixture + test repair (B1).
- Platform claim = code (B2 decision can be “POSIX only” with doc/CI only — no Windows code yet).
- Stdout/stderr split and single error prefix (B4).
- Process RAII + timeout skeleton (part of B3).
- Version string → `0.1.0` or keep 1.0.0 but stop implying finished (honesty).

### Phase 1 — Core Functional Readiness

Make Key/BPM behavior defined and safe on real files. **Depends on Phase 0 fixture** so changes are measurable.

- Resample + duration/size caps (B3).
- CLI flag parsing, `--help`/`--version`.
- Decode error taxonomy; regular-file checks.
- DSP parameter pinning; tempo candidates; key pipeline improvements **with tests**.
- JSON schema stability.

### Phase 2 — Architecture and Reliability

Reshape the wrapper so it can be tested and ported. **Depends on Phase 0 stream/process contracts** so refactors do not re-merge stderr.

- Split C++ header/impl; discovery order; `/proc/self/exe` (Linux) / equivalent.
- Windows process backend **only if** Phase 0 chose cross-platform.
- Logging/debug env; signal reporting; SIGINT.
- Explicit “Python is the engine” module layout (`scripts/` → importable package if useful).

### Phase 3 — Testing and Quality Infrastructure

**Depends on Phase 1 DSP/limits** (otherwise the matrix tests the old unbounded pipeline).

- Corpus + tolerances; edge fixtures; C++ tests; sanitizers; pin/lock dependencies; CMake test targets.

### Phase 4 — UX and Product Polish

**Depends on Phase 1 CLI/JSON** so polish does not paint over broken output.

- Progress, verbose, confidence copy, README rewrite, troubleshooting strings matching code.

### Phase 5 — Packaging and Release Engineering

**Depends on Phase 2 install layout and Phase 3 pins.**

- `install()`, optional CPack/tarball, third-party license note, macOS CI, Windows CI if applicable, drop-the-binary docs.

### Phase 6 — Final Production Verification

**Depends on Phases 0–5.**

- Full §9 matrix, sanitizer + warning clean, checklist §10, no known P0/P1 open.

**Adaptations from a generic template:** There is no existing GUI to polish (Phase 4 is CLI-only). There is no current package to repair (Phase 5 is greenfield). Native C++ DSP is **not** in Phase 0–3; it is optional later (§12).

## 8. Implementation Tasks

### Phase 0 — Critical Stabilization

#### T0.1 — Create a self-contained A-minor 120 BPM fixture

- **Objective:** Restore the only real-audio contract without relying on a missing binary.
- **Rationale:** B1. Tests and README assume this file.
- **Likely files:** `tests/test_pybridge.py`, new `tests/conftest.py` or `tests/generate_fixture.py`, `tests/integration_test.sh`, optional `samples/README.md`. Do **not** invent a committed WAV unless generation is rejected.
- **Approach:** Synthesize a short (8–16 s) mono 22050 Hz WAV: A-minor triad (A3/C4/E4) with 2 Hz amplitude pulses (120 BPM). Write to `tmp_path` or `tests/.generated/` (gitignored) and share the path via a pytest fixture env var for the shell test.
- **Dependencies:** None.
- **Risk:** A static triad may still confuse `beat_track`; if so, add a soft kick on each beat (still generated).
- **Complexity:** Medium
- **Acceptance:** `test_analyze_audio_on_sample` finds a file and asserts `key == "A minor"` and BPM in a **tight** band (see T0.2).
- **Verification:** pytest locally and in CI; hex/header of the WAV is RIFF.

#### T0.2 — Repair Python and integration assertions

- **Objective:** Tests prove JSON + key + BPM, not a substring on a missing path.
- **Rationale:** B1, §5.1 integration gap.
- **Likely files:** `tests/test_pybridge.py`, `tests/integration_test.sh`, `.github/workflows/ci.yml`
- **Approach:** Fixture from T0.1. Integration: resolve binary as `$KEY_BPM_BINARY` or `build/Key-BpmFinder` or fail with a clear message; `python -c 'json.loads'` the stdout; assert key; assert BPM in `[117, 123]` once the fixture is known good (adjust only with evidence).
- **Dependencies:** T0.1
- **Risk:** Host `beat_track` variance across librosa versions.
- **Complexity:** Small
- **Acceptance:** CI steps “Run Python unit tests” and “Run integration test” pass on ubuntu-latest with Python 3.11.
- **Verification:** GitHub Actions on a PR; do not widen BPM bounds to hide failure.

#### T0.3 — Align platform claims with POSIX-only code

- **Objective:** README/CMake/CI tell one story.
- **Rationale:** B2.
- **Likely files:** `README.md`, `CMakeLists.txt` (remove or gate MSVC `/W4` with a comment that the source is POSIX until T2.3), `.github/workflows/ci.yml` (optional `macos-latest` later).
- **Approach:** Default decision: **POSIX-only v0.x**. State Linux CI-supported, macOS best-effort until Phase 5. Remove MSVC from prerequisites.
- **Dependencies:** None (product decision).
- **Risk:** Low if Windows is deferred.
- **Complexity:** Small
- **Acceptance:** No remaining “MSVC works” claim; CMake does not imply a Windows build of `bridge_runner.hpp`.
- **Verification:** README review; grep MSVC/Windows.

#### T0.4 — Split child stdout/stderr and fix error prefix

- **Objective:** JSON on stdout is only JSON; one `Error:` on failure.
- **Rationale:** B4, §5.6 double prefix.
- **Likely files:** `include/bridge_runner.hpp`, `src/main.cpp`, `scripts/PyBridge.py`, tests
- **Approach:** Two pipes or `posix_spawn` dup2 stderr to a dedicated pipe. `run_process_capture` returns `{stdout, stderr, status}`. Success: print stdout; copy stderr to parent stderr. Failure: throw trimmed stderr/stdout. Python: print errors to stderr without relying on parent duplication.
- **Dependencies:** None, but do before JSON integration hardens (T0.2 can land with a note if ordered same PR).
- **Risk:** Integration currently greps merged stdout — update it in the same change.
- **Complexity:** Medium
- **Acceptance:** Warning injection test; missing-file message matches README after T4.2.
- **Verification:** pytest + integration `json.loads`.

#### T0.5 — Harden process lifetime (RAII, wait, timeout)

- **Objective:** No fd leaks; bounded wait.
- **Rationale:** B3 process side; §5.3.
- **Likely files:** `include/bridge_runner.hpp` (later `src/bridge_runner.cpp`)
- **Approach:** Fd owner type; check `posix_spawn_file_actions_*`; EINTR loops; if `read < 0`, fail; `waitpid` loop; timeout via `poll`/`waitpid WNOHANG` + `kill(SIGKILL)` (POSIX). Default timeout e.g. 120 s, env `KEY_BPM_TIMEOUT_SEC`.
- **Dependencies:** T0.4 if the pipe layout changes — implement together.
- **Risk:** Timeout tests are OS-sensitive.
- **Complexity:** Medium
- **Acceptance:** Unit-level test with a fake `python` script that sleeps past timeout (can live under `tests/` as a tiny helper `.py`).
- **Verification:** pytest spawning the **built** binary or a small C++ test; ASan later (T3.4).

#### T0.6 — Record honest project version

- **Objective:** Stop advertising CMake `1.0.0` as a released product.
- **Rationale:** §5.17.
- **Likely files:** `CMakeLists.txt`
- **Approach:** `VERSION 0.1.0` until Phase 6.
- **Dependencies:** None.
- **Risk:** None.
- **Complexity:** Small
- **Acceptance:** Version is 0.1.0 (or documented pre-release).
- **Verification:** `grep VERSION CMakeLists.txt`.

### Phase 1 — Core Functional Readiness

#### T1.1 — Fixed analysis sample rate and resource caps

- **Objective:** Predictable DSP and bounded memory.
- **Rationale:** B3, §5.2 decode.
- **Likely files:** `scripts/PyBridge.py`, tests, README
- **Approach:** `librosa.load(..., sr=22050, mono=True, duration=max_sec)` plus file-size check (`stat`). Defaults: e.g. 50 MB and 10 minutes, overridable by flags/env later. JSON: add `analysis_sample_rate` and keep native if you load twice or use `sf.info` — prefer `soundfile.info` for native rate/duration **without** loading 96 kHz fully, then load capped/resampled.
- **Dependencies:** T0.1 so caps do not break the fixture.
- **Risk:** `soundfile.info` fails on some formats that ffmpeg would decode — fall back with a clear error.
- **Complexity:** Medium
- **Acceptance:** 1-hour synthetic header/size test fails fast; fixture still passes; JSON reports analysis rate 22050.
- **Verification:** pytest.

#### T1.2 — Regular-file and decode error mapping

- **Objective:** Predictable errors for garbage inputs.
- **Rationale:** §5.1, §5.2 formats.
- **Likely files:** `include/bridge_runner.hpp`, `scripts/PyBridge.py`
- **Approach:** C++ `is_regular_file`. Python catch load failures → `ValueError("Unsupported or corrupt audio: …")`.
- **Dependencies:** T0.4 for clean messages.
- **Risk:** Over-broad catch hides bugs — keep debug mode.
- **Complexity:** Small
- **Acceptance:** Directory, missing, empty, and a truncated RIFF fail with distinct messages; tests for each.
- **Verification:** pytest.

#### T1.3 — C++ CLI parity with argparse

- **Objective:** `--json` anywhere; `--help`; `--version`.
- **Rationale:** §5.1.
- **Likely files:** `src/main.cpp`
- **Approach:** Tiny flag loop; do not add getopt-only if Windows remains a future goal — a manual loop is enough.
- **Dependencies:** T0.6 for version string (can hardcode from a `#define` later).
- **Risk:** Low.
- **Complexity:** Small
- **Acceptance:** `Key-BpmFinder --help` exits 0; `file --json` works; `--json` alone exits 2/1 with usage, not “file does not exist: --json”.
- **Verification:** integration script cases.

#### T1.4 — Pin DSP parameters and librosa usage

- **Objective:** Stable chroma/tempo settings across versions.
- **Rationale:** §5.2 defaults / unpinned deps.
- **Likely files:** `scripts/PyBridge.py`, `requirements.txt`
- **Approach:** Explicit `n_fft=2048`, `hop_length=512`, `win_length=2048` for chroma; explicit `beat_track` hop if the API allows. Comment why. Pin `librosa` to a tested minor (e.g. `>=0.10,<0.12`) **after** CI proves it.
- **Dependencies:** T0.2 green on current lower bounds first.
- **Risk:** Pin too tight for users.
- **Complexity:** Small
- **Acceptance:** Parameters are literals in `analyze_audio`; requirements have an upper bound used in CI.
- **Verification:** pytest unchanged for synthetic tests.

#### T1.5 — Tempo candidates and octave fold

- **Objective:** Reduce ½×/2× as a **defined** behavior.
- **Rationale:** §5.2 tempo.
- **Likely files:** `scripts/PyBridge.py`, tests
- **Approach:** From `beat_track` (and/or `librosa.feature.tempo` if used), evaluate `{t/2, t, 2t}` in a musical range (e.g. 56–200 BPM) against onset-strength autocorrelation; pick winner; emit `bpm`, `bpm_candidates`, `bpm_confidence`.
- **Dependencies:** T0.1 fixture; T1.4 pins.
- **Risk:** Overfitting to the synthetic kick; validate with more generated tempi (T3.1).
- **Complexity:** Medium
- **Acceptance:** Generated 70/120/174 fixtures land in tolerance after fold; JSON schema documented.
- **Verification:** pytest tolerances in §9.

#### T1.6 — Key pipeline hardening (not a new ML model)

- **Objective:** Same KS decision, better chroma.
- **Rationale:** §5.2 key weaknesses.
- **Likely files:** `scripts/PyBridge.py`, `tests/test_pybridge.py`
- **Approach:** `chroma_cqt` (or STFT+CQT vote) at the analysis `sr`; optional `librosa.effects.harmonic`; `librosa.estimate_tuning` then `win_chroma` shift. Keep KS + existing unit tests. Emit `alternate_key` (second best) so relative-mode ambiguity is visible.
- **Dependencies:** T1.1 (fixed sr), T0.1.
- **Risk:** CQT is slower — acceptable under duration cap. Do not claim higher accuracy until T3.1.
- **Complexity:** Medium
- **Acceptance:** Synthetic profile tests still pass; generated A-minor fixture still `A minor`; JSON includes `alternate_key`.
- **Verification:** pytest; later corpus.

### Phase 2 — Architecture and Reliability

#### T2.1 — Split C++ implementation out of the header

- **Objective:** Testable, includable API without pulling `unistd.h` into every TU unnecessarily.
- **Rationale:** §5.3, §5.4.
- **Likely files:** `include/bridge_runner.hpp`, new `src/bridge_runner.cpp`, `CMakeLists.txt`
- **Approach:** Declarations in the header; POSIX body in `.cpp`. `target_sources` the new file.
- **Dependencies:** T0.4, T0.5 (avoid moving buggy code twice — split immediately after those).
- **Risk:** Trivial link errors.
- **Complexity:** Small
- **Acceptance:** Build lists both sources; header has no `posix_spawn`.
- **Verification:** CMake build in `/tmp`.

#### T2.2 — Deterministic bridge discovery

- **Objective:** The copied/installed `PyBridge.py` wins over cwd junk.
- **Rationale:** §5.3, B5.
- **Likely files:** `src/bridge_runner.cpp`, tests
- **Approach:** Order: `KEY_BPM_BRIDGE` env (documented), `realpath` of executable dir, install `share/keybpm/PyBridge.py` if you add it, then cwd. `is_regular_file`. Linux: `/proc/self/exe`.
- **Dependencies:** T2.1
- **Risk:** macOS needs `_NSGetExecutablePath` — stub “absolute argv0” until T5.2.
- **Complexity:** Medium
- **Acceptance:** Running from a directory that contains a decoy `scripts/PyBridge.py` still uses the binary-adjacent script unless env overrides.
- **Verification:** Integration test with a decoy cwd.

#### T2.3 — Windows process backend (optional)

- **Objective:** Honor cross-platform **only if** Phase 0 reversed T0.3.
- **Rationale:** B2 option (b).
- **Likely files:** `src/bridge_runner.cpp`, `CMakeLists.txt`, new workflow job
- **Approach:** `#ifdef _WIN32` `CreateProcessW` + anonymous pipes. Default interpreter `python`.
- **Dependencies:** T0.3 decision; T2.1; T0.4 contract.
- **Risk:** High (quoting, encodings, CI minutes).
- **Complexity:** Large
- **Acceptance:** MSVC build + analyze fixture on `windows-latest`.
- **Verification:** CI job.
- **Note:** If T0.3 stays POSIX-only, **skip** this task (see §12).

#### T2.4 — Debug / signal observability

- **Objective:** Supportable failures.
- **Rationale:** §5.6, §5.16.
- **Likely files:** `src/bridge_runner.cpp`, `src/main.cpp`, `scripts/PyBridge.py`
- **Approach:** `KEYBPM_DEBUG` / `-v`: timings, chosen script path, python path, signal if `WIFSIGNALED`.
- **Dependencies:** T0.5, T2.1
- **Risk:** Accidental JSON pollution — verbose **only** stderr.
- **Complexity:** Small
- **Acceptance:** `-v --json` still `json.loads`s stdout.
- **Verification:** integration test.

#### T2.5 — SIGINT cancels the child

- **Objective:** Ctrl-C does not leave a Python/librosa orphan.
- **Rationale:** §5.5, §5.3 threads.
- **Likely files:** `src/bridge_runner.cpp`
- **Approach:** Forward SIGINT/SIGTERM to `pid`; still reap.
- **Dependencies:** T0.5
- **Risk:** Test flakiness.
- **Complexity:** Medium
- **Acceptance:** Manual + a test that starts a sleep child and signals the parent.
- **Verification:** POSIX-only test.

### Phase 3 — Testing and Quality Infrastructure

#### T3.1 — Known BPM/key mini-corpus

- **Objective:** Tolerance-based validation beyond one triad.
- **Rationale:** §5.9, user requirement for known-BPM/key corpus.
- **Likely files:** `tests/` generators, `tests/test_corpus.py`
- **Approach:** Generate: 100/120/140 BPM kicks; A minor / G major / C major sustained triads; one relative-ambiguity mix. Table-driven expected key and BPM ± tolerance (`§9`). No copyrighted commercial tracks in-repo.
- **Dependencies:** T1.5, T1.6, T0.1
- **Risk:** Generators that don’t excite `beat_track`.
- **Complexity:** Medium
- **Acceptance:** Documented table in `tests/` or README; CI runs it.
- **Verification:** pytest.

#### T3.2 — Edge and malformed fixtures

- **Objective:** Cover silence, 100 ms clip, empty WAV, directory, missing, huge size flag, stereo, 8 kHz, 96 kHz.
- **Rationale:** §5.2, B3.
- **Likely files:** `tests/test_pybridge.py`, `tests/test_edges.py`
- **Approach:** Generate in pytest; assert error codes/messages.
- **Dependencies:** T1.1, T1.2
- **Risk:** Low.
- **Complexity:** Medium
- **Acceptance:** Each row in §9 “edge” list has a test.
- **Verification:** pytest.

#### T3.3 — C++-level tests for the runner

- **Objective:** Discovery, timeout, stderr isolation without full librosa.
- **Rationale:** §5.9.
- **Likely files:** new `tests/test_bridge.cpp` or Python tests that launch `Key-BpmFinder` with a stub `KEY_BPM_PYTHON` script.
- **Approach:** Prefer **stub interpreter scripts** to avoid Catch2/GTest dependency: `KEY_BPM_PYTHON` pointing at `tests/fake_python.py`.
- **Dependencies:** T0.4, T0.5, T2.2
- **Risk:** Path quoting.
- **Complexity:** Medium
- **Acceptance:** Fake python prints JSON; warnings on stderr; timeout fake sleeps.
- **Verification:** `tests/integration_test.sh` extended or pytest `subprocess`.

#### T3.4 — Sanitizers and warning policy

- **Objective:** Catch UB in the runner.
- **Rationale:** §5.3.
- **Likely files:** `CMakeLists.txt`, `.github/workflows/ci.yml`
- **Approach:** `option(KEYBPM_SANITIZE "ASan+UBSan" OFF)`. CI job: GCC sanitize + stub tests (not necessarily full librosa under ASan unless wheels cooperate).
- **Dependencies:** T2.1, T3.3
- **Risk:** Python/librosa + ASan in one process is **not** applicable (separate process). Sanitize **C++ only**.
- **Complexity:** Medium
- **Acceptance:** Sanitize job runs T3.3; clean exit.
- **Verification:** CI.

#### T3.5 — Lock Python dependencies for CI

- **Objective:** Reproducible numbers and supply-chain baseline.
- **Rationale:** §5.11.
- **Likely files:** new `requirements.lock` (or `constraints.txt`), `ci.yml`, `requirements.txt`
- **Approach:** Compile a lock on ubuntu-latest Python 3.11; CI `pip install -r requirements.lock`. Leave README with the abstract `requirements.txt`.
- **Dependencies:** T0.2 green.
- **Risk:** Lock drift.
- **Complexity:** Small
- **Acceptance:** CI uses the lock; comment on how to regenerate.
- **Verification:** CI logs show pinned versions.

### Phase 4 — UX and Product Polish

#### T4.1 — Progress and verbose human mode

- **Objective:** Long files look alive.
- **Rationale:** §5.5.
- **Likely files:** `scripts/PyBridge.py`, `src/main.cpp`
- **Approach:** stderr `Loading…` / `Estimating tempo…` / `Estimating key…` when not `--json` or when `-v`.
- **Dependencies:** T0.4
- **Risk:** None if stderr-only.
- **Complexity:** Small
- **Acceptance:** `--json` stdout unchanged.
- **Verification:** integration.

#### T4.2 — Rewrite README to match code

- **Objective:** A user on this branch can follow docs without dead samples or MSVC.
- **Rationale:** §5.14.
- **Likely files:** `README.md`
- **Approach:** Platform table; formats; limits; confidence meaning; exact error strings; how to generate/run tests; JSON field list; drop “more accurate” or qualify it.
- **Dependencies:** T0.3, T1.1, T1.3
- **Risk:** Drift — do this after flags/limits exist.
- **Complexity:** Small
- **Acceptance:** Every command in README works on a clean Ubuntu venv.
- **Verification:** Manual + CI using the same commands.

#### T4.3 — Confidence and ambiguity UX

- **Objective:** Users see top-2 keys and a plain-language confidence.
- **Rationale:** §5.5, T1.6.
- **Likely files:** `scripts/PyBridge.py`, README
- **Approach:** Print `Alternate key:` and `Confidence: low` using temporary thresholds labeled “unvalidated.”
- **Dependencies:** T1.6
- **Risk:** Fake precision — keep “unvalidated” until a corpus exists.
- **Complexity:** Small
- **Acceptance:** Human output documents the caveat.
- **Verification:** fixture test snapshots (careful with floats — assert prefixes).

### Phase 5 — Packaging and Release Engineering

#### T5.1 — CMake install layout

- **Objective:** `cmake --install` produces a runnable prefix.
- **Rationale:** B5.
- **Likely files:** `CMakeLists.txt`, README
- **Approach:** Install `Key-BpmFinder` to `bin/`; `PyBridge.py` to `share/keybpm/`; discovery looks there (T2.2).
- **Dependencies:** T2.2
- **Risk:** RPATH / relocatable prefix.
- **Complexity:** Medium
- **Acceptance:** Install to `/tmp/keybpm-prefix` and run without the git tree (venv still required).
- **Verification:** CI step.

#### T5.2 — macOS CI and executable-path discovery

- **Objective:** Second POSIX platform evidence.
- **Rationale:** §5.12.
- **Likely files:** `ci.yml`, `src/bridge_runner.cpp`
- **Approach:** `macos-latest` job; implement Apple executable path if T2.2 was Linux-only.
- **Dependencies:** T2.2, T0.2
- **Risk:** librosa wheels on macOS runners.
- **Complexity:** Medium
- **Acceptance:** Same pytest + integration on macOS.
- **Verification:** CI.

#### T5.3 — Distribution archive and license notice

- **Objective:** A source + notes tarball; third-party license acknowledgment.
- **Rationale:** §5.11, §5.15.
- **Likely files:** README or `THIRD_PARTY.md`, optional CPack
- **Approach:** Document “source + venv” as the supported distro for v0.x. List MIT + “pip freeze licenses are yours to comply with.”
- **Dependencies:** T3.5, T5.1
- **Risk:** Incomplete license inventory — say so.
- **Complexity:** Small
- **Acceptance:** `THIRD_PARTY.md` exists and is honest.
- **Verification:** File review.

#### T5.4 — No CD until checklist

- **Objective:** Do not add auto-publish.
- **Rationale:** No secrets, no release assets yet.
- **Likely files:** none (explicit non-task)
- **Approach:** Keep `ci.yml` as verify-only.
- **Dependencies:** Phase 6 sign-off before any release workflow.
- **Risk:** Someone adds a tokenful publish job too early.
- **Complexity:** —
- **Acceptance:** No deploy job in `.github/workflows/`.
- **Verification:** File review.

### Phase 6 — Final Production Verification

#### T6.1 — Execute the full test matrix

- **Objective:** Evidence, not intention.
- **Rationale:** This audit could not run builds.
- **Likely files:** CI + local notes
- **Approach:** Run §9 on Linux (required) and macOS (if T5.2). Record librosa versions.
- **Dependencies:** T3.1–T3.5, T5.2
- **Risk:** Residual flakes.
- **Complexity:** Medium
- **Acceptance:** Matrix rows checked in §10.
- **Verification:** CI logs kept.

#### T6.2 — Sanitizer and warning clean confirmation

- **Objective:** Runner has no ASan/UBSan hits.
- **Rationale:** T3.4.
- **Dependencies:** T3.4
- **Complexity:** Small
- **Acceptance:** Sanitize job green on `main`.
- **Verification:** CI.

#### T6.3 — Documentation and claim audit

- **Objective:** Every README claim is true on HEAD.
- **Rationale:** §5.14 over-claims found in this audit.
- **Dependencies:** T4.2
- **Complexity:** Small
- **Acceptance:** Grep for MSVC, missing sample paths, “1.0.0”, “more accurate” without caveat — none remain unless true.
- **Verification:** Review.

#### T6.4 — Release checklist sign-off

- **Objective:** Human gate.
- **Rationale:** §10.
- **Dependencies:** All P0/P1 closed.
- **Complexity:** Small
- **Acceptance:** All boxes in §10 checked with evidence links.
- **Verification:** Maintainer.

## 9. Recommended Test Matrix

### 9.1 Platforms / compilers / configs

| Row | Platform | Compiler | Config | Status now |
|---|---|---|---|---|
| L1 | Ubuntu (CI `ubuntu-latest`) | GCC (runner default) | Debug + Release | CI exists; **blocked on missing sample** |
| L2 | Ubuntu | GCC | ASan+UBSan, C++ tests/stubs | **Missing** |
| L3 | Fedora 43 host (this machine) | system GCC/Clang | Release, out-of-repo `/tmp` build | **Not run** (Shell rejected) |
| M1 | macOS latest | AppleClang | Release | **Missing** |
| W1 | Windows / MSVC | MSVC | Release | **Not supported by source** — skip unless T2.3 |

Python: CI 3.11 required; add 3.10 and 3.12. Treat 3.14 as **unsupported** until proven (`numba` risk).

### 9.2 Audio formats and shapes

| Fixture | Expectation |
|---|---|
| Generated WAV 22050 mono 16-bit | Success |
| Generated WAV 44100 stereo | Success (mono mix); key/BPM within tolerance |
| Generated WAV 8000 and 96000 | Success after resample; caps apply to **decoded** duration not just file bytes |
| FLAC (if soundfile supports) | Success |
| OGG/Vorbis | Success or mapped unsupported |
| MP3 | Success only if ffmpeg present; otherwise mapped error (do not fail CI unless ffmpeg installed) |
| `.txt` / random bytes | `decode_failed` / unsupported |
| Truncated RIFF | decode error, no hang |
| Empty file | explicit error |
| Directory | explicit error (C++ and Python) |
| Missing path | explicit error |

### 9.3 Duration / abuse

| Fixture | Expectation |
|---|---|
| 100 ms tone | `too_short` |
| Digital silence 5 s | key error (existing normalize) and/or `too_silent` |
| 8–16 s generated musical fixture | success |
| File size > cap | fail before full decode |
| `duration` > cap | analyze first N seconds **or** refuse — pick one and test it |
| Sleep stub via `KEY_BPM_PYTHON` | timeout, non-zero, no zombie |

### 9.4 Known BPM / key fixtures and tolerances

Generate in-repo; do not depend on missing `samples/test-tone-a-minor-120bpm.wav` until it exists.

| ID | Content | Key expect | BPM expect | Tolerance |
|---|---|---|---|---|
| K1 | A-minor triad + 120 BPM pulses/kicks | `A minor` | 120 | ±2 BPM or ±2% |
| K2 | G-major triad + 100 BPM | `G major` | 100 | same |
| K3 | C-major triad + 140 BPM | `C major` | 140 | same |
| K4 | Kick-only 174 BPM (no pitch) | key may be low-confidence; **do not** require a specific key | 174 after octave fold | ±3 BPM |
| K5 | 70 BPM kicks | key not required | 70 (not 140) after fold | ±3 BPM |
| K6 | KS-rotated synthetic chroma (existing tests) | `A minor` / `G major` | n/a | score ≈ 1, abs 1e-9 |

**Octave rule:** If `|bpm - expected*2|` or `|bpm - expected/2|` is smaller than `|bpm - expected|` before fold, the **algorithm** should fold; the **test** should assert the folded value. Until T1.5 ships, treat K4/K5 as expected-fail / skip.

**Key rule:** Require exact string on K1–K3 **after** T1.6. If a change flips relative mode, fail the test; do not loosen to “A minor or C major” without documenting ambiguity and emitting `alternate_key`.

### 9.5 Regression / CLI

- `--json` stdout parses as JSON (`json.loads`).
- Human mode contains `BPM:` and `Key:` lines.
- `--help` / usage.
- `KEY_BPM_PYTHON` stub.
- Decoy cwd `scripts/PyBridge.py` (after T2.2).
- Double-prefix must not appear.

### 9.6 Sanitizers and static analysis

- ASan+UBSan on C++ stub tests (T3.4).
- Optional later: `clang-tidy` on `src/*.cpp`; `ruff` on `scripts/` and `tests/`.
- No need for full librosa under ASan.

### 9.7 CI jobs (target)

1. `pytest` + locked deps (Ubuntu, Python 3.11).
2. CMake build + integration (same workspace, `KEY_BPM_PYTHON` = job venv).
3. Later: Python 3.10 and 3.12 pytest (same OS, no need to rebuild C++ per version if the binary only execs `python`).
4. Later: macOS pytest + build + integration (T5.2).
5. Later: ASan/UBSan C++ stub job (T3.4).
6. Windows job: **only** after T2.3.

Current CI (`.github/workflows/ci.yml`) is jobs 1–2 on Ubuntu without a lockfile and without a fixture — it is the right shape, not yet green.

## 10. Production Release Checklist

Grounded in **this** repository. Check a box only with evidence from HEAD.

### Product contract

- [ ] `samples/test-tone-a-minor-120bpm.wav` exists **or** tests generate an equivalent fixture (T0.1). No README command points at a missing path.
- [ ] `pytest tests/` passes on Ubuntu CI Python 3.11 without extra manual files.
- [ ] `tests/integration_test.sh` (or successor) runs `Key-BpmFinder --json` and `json.loads`s stdout; asserts `A minor` and BPM within the documented tolerance.
- [ ] README platform list matches code: POSIX-only **or** a green MSVC job exists. No leftover “MSVC just works” line if `bridge_runner` is still POSIX.
- [ ] CMake version is `0.x` until this checklist is complete, **or** `1.0.0` is used only after every P0/P1 below is done.

### CLI and API

- [ ] `Key-BpmFinder --help` and `--version` work (`src/main.cpp`).
- [ ] `--json` is accepted before or after the audio path; `--json` alone is usage, not “file does not exist: --json”.
- [ ] Success `--json` stdout is a single JSON object (no librosa warnings mixed in). Fields documented: at least `bpm`, `key`, `key_score`, `key_confidence`, `sample_rate` / `analysis_sample_rate`, `duration_seconds`.
- [ ] Failure prints exactly one `Error:` prefix on stderr; exit status non-zero.
- [ ] `KEY_BPM_PYTHON` is documented and used by CI the same way as README.

### Analysis safety and DSP

- [ ] Analysis sample rate is fixed and tested (T1.1).
- [ ] File-size and duration (or wall-clock) caps exist and have tests (T1.1, T0.5).
- [ ] Non-regular files (directories already; FIFOs/devices if feasible) are rejected in C++ (`is_regular_file`).
- [ ] Decode failures map to a user-facing message, not a raw stack, unless debug is on (T1.2).
- [ ] Tempo octave policy is implemented **or** explicitly documented as “single `beat_track` value, ½×/2× possible” with K4/K5 skipped.
- [ ] Key method (KS + which chroma) and confidence meaning are documented; `alternate_key` recommended (T1.6 / T4.3).
- [ ] K1–K3 generated fixtures pass with §9.4 tolerances.

### C++ / process

- [ ] Child stdout/stderr are separate pipes; JSON cannot be polluted by warnings (T0.4).
- [ ] Process helper checks spawn/file-action/read/wait returns; timeout kills the child (T0.5).
- [ ] Bridge discovery prefers binary-adjacent / install path over cwd (T2.2).
- [ ] Header no longer is the only home of POSIX calls (T2.1) **or** a written exception exists for the tiny-prototype layout.

### Build, CI, deps

- [ ] `cmake -S . -B <out-of-repo-or-build/>` and `cmake --build` succeed on Ubuntu.
- [ ] `.github/workflows/ci.yml` is green on a PR from this branch.
- [ ] Python deps used by CI are pinned/locked (T3.5).
- [ ] Supported CPython range is stated; 3.14 is included only if a job passed.
- [ ] Optional: ASan/UBSan job green on C++ stub tests (T3.4).
- [ ] `cmake --install` installs `Key-BpmFinder` and `PyBridge.py` to a prefix that T2.2 can find (T5.1) — required for any binary-tarball release.

### Docs, license, hygiene

- [ ] README commands match actual error strings (`Audio file does not exist` vs “not found”).
- [ ] Formats, ffmpeg, and `KEY_BPM_PYTHON` are documented without claiming Windows if unsupported.
- [ ] “More accurate” claim is removed or limited to “KS-on-chroma vs old tuning proxy,” with no implied corpus accuracy.
- [ ] `LICENSE` (MIT) remains; `THIRD_PARTY.md` or README notes pip-stack licenses (T5.3).
- [ ] No secrets in the tree; no deploy job with tokens (T5.4).
- [ ] `.gitignore` still excludes `/build/`, venvs, and generated fixtures if those are local.

### Explicitly out of scope unless product direction changes

- [ ] N/A: desktop GUI, live input, commercial-track corpus, native C++ DSP rewrite, GitHub Releases automation.

## 11. Recommended Implementation Order

Do this sequence. Parallelism is called out.

1. **T0.1 fixture generation** — foundation for every audio test. Nothing that asserts on real PCM should merge before this.
2. **T0.4 + T0.5 together** (stderr split, RAII, timeout) — one C++ change set; T0.2’s integration `json.loads` depends on clean stdout. **Sequential with T0.2.**
3. **T0.2 test/CI repair** — first green CI. **Highest-risk** until it passes because the advertised pipeline is currently untestable.
4. **T0.3 + T0.6** (docs/platform + version) — **independent** of T0.1–T0.2; can be the same PR or a parallel docs PR. Quick win.
5. **T1.3 CLI flags** — **independent** once `main.cpp` is touched; quick win; do not block DSP.
6. **T1.1 + T1.2** (caps, regular file, decode errors) — safety before inviting larger files. **Sequential after T0.2** so regressions are visible.
7. **T1.4 pin DSP knobs** — small; before T1.5/T1.6 so those changes are reproducible.
8. **T1.5 tempo fold, then T1.6 key chroma** — **highest-risk DSP**. Sequential; keep T0.1/T3.1 fixtures as the oracle. Do not start a C++ rewrite here.
9. **T2.1 split header, then T2.2 discovery** — architecture. After process contracts (T0.4/T0.5) are stable.
10. **T2.4 + T2.5** (debug, SIGINT) — after the runner is in `.cpp`.
11. **T3.1 corpus + T3.2 edges + T3.3 stub runner tests** — T3.3 can start as soon as T0.4/T0.5/T2.2 exist; T3.1 wants T1.5/T1.6.
12. **T3.4 sanitizers + T3.5 lockfile** — lockfile can be **parallel** as soon as T0.2 is green; sanitizers after T3.3.
13. **T4.1–T4.3 UX/README** — after JSON/limits/flags exist (otherwise docs rot).
14. **T5.1 install, T5.2 macOS, T5.3 licenses** — after discovery (T2.2) and pins (T3.5).
15. **T2.3 Windows** — **delayed** unless T0.3 is reversed. Do not interleave with DSP work.
16. **T6.1–T6.4** — only when P0/P1 items are closed.

**Independent / quick wins:** T0.3, T0.6, T1.3, README error-string fixes, adding `json.loads` to the integration script once stdout is clean.

**Foundations:** T0.1, T0.4, T0.5, T1.1.

**Highest-risk:** T0.2 (proves the stack), T1.5/T1.6 (changes answers), T2.2 (wrong script = silent wrong tool), T2.3 (port).

**Delayed:** Windows, GUI, native DSP, CD/releases, commercial corpus, live capture.

## 12. Deferred / Optional Improvements

Keep these off the critical path to a truthful v0.2 CLI release.

- **Desktop GUI** (drag-and-drop, progress bar, accessibility tree). The repo is a CLI; building a UI now would freeze the wrong architecture.
- **Live / microphone input** and DAW plugin (VST/CLAP). No device layer exists.
- **Native C++ DSP** (FFTW, custom chroma, no Python). Only justified if a no-Python ship is a hard requirement; months of work vs pinning librosa.
- **Windows port (T2.3)** if the product decision in T0.3 is POSIX-only.
- **Learned key/tempo models** (madmom, essential, CNNs). Needs a real labeled corpus and license review; current KS+`beat_track` is enough for v0.x if documented honestly.
- **Commercial-track accuracy study.** Do not add copyrighted audio to the repo. If done later, keep fixtures private and publish only metrics.
- **Batch directory mode, watch folders, M3U, tagging writers (ID3/Vorbis).** Feature expansion, not readiness.
- **Camelot / Open Key notation, key-lock mixing helpers.** Product extras.
- **Embedded CPython / PyInstaller / one-file exe.** Packaging option after T5.1; high maintenance.
- **clang-tidy, ruff, pre-commit, Dependabot, CodeQL, fuzzing libsndfile inputs.** Good hygiene after CI is green.
- **CPack/Homebrew/apt/winget.** After install layout exists and someone will maintain bottles.
- **GitHub Releases / signed binaries / SBOM.** After Phase 6; no tokenful CD in v0.x.
- **Parallel feature extraction, GPU, streaming STFT.** Speculative performance; measure T1.1 first.
- **`KEY_BPM_PYTHON` hardening for multi-user services.** This is a local CLI.
- **Relative-major disambiguation research, section-level key changes, downbeat snapping, time-signature estimation.** Research backlog.

### Deferred on purpose because the current design is already acceptable

- Shell-less `posix_spawnp` argv passing — keep; do not “improve” via `popen`.
- MIT for first-party code.
- Dual human/JSON output concept.
- KS profile constants and the rotate-to-identity unit tests.
- `KEY_BPM_PYTHON` as a venv escape hatch.
- CMake warning flags and post-build copy of `PyBridge.py` (adjust discovery order, do not remove the copy).
