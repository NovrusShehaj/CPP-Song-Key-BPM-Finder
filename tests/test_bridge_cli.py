"""C++ runner tests that launch Key-BpmFinder with a stub interpreter."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from generate_fixture import write_wav

FAKE_PYTHON = Path(__file__).resolve().parent / "fake_python.py"


def _stub_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["KEY_BPM_PYTHON"] = sys.executable
    env["KEY_BPM_BRIDGE"] = str(FAKE_PYTHON)
    env["KEY_BPM_FAKE_MODE"] = "json"
    if extra:
        env.update(extra)
    return env


def _run_binary(
    binary: Path,
    args: list[str],
    extra_env: dict[str, str] | None = None,
    timeout: float = 15.0,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(binary), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(cwd or Path(__file__).resolve().parents[1]),
        env=_stub_env(extra_env),
    )


@pytest.mark.requires_binary
def test_help_exits_zero(keybpm_binary: Path):
    result = _run_binary(keybpm_binary, ["--help"])
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "KEY_BPM_PYTHON" in result.stdout


@pytest.mark.requires_binary
def test_version_exits_zero(keybpm_binary: Path):
    result = _run_binary(keybpm_binary, ["--version"])
    assert result.returncode == 0
    assert "0.1.0" in result.stdout


@pytest.mark.requires_binary
def test_json_alone_is_usage(keybpm_binary: Path):
    result = _run_binary(keybpm_binary, ["--json"])
    assert result.returncode == 2
    assert "Usage:" in result.stderr
    assert "does not exist: --json" not in result.stderr


@pytest.mark.requires_binary
def test_json_after_path_with_stub(keybpm_binary: Path, tmp_path: Path):
    audio = write_wav(tmp_path / "stub.wav", duration=3.0, freqs=(220.0,), kick=False)
    result = _run_binary(keybpm_binary, [str(audio), "--json"])
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["key"] == "A minor"
    assert result.stdout.lstrip().startswith("{")


@pytest.mark.requires_binary
def test_warning_on_stderr_does_not_break_json(keybpm_binary: Path, tmp_path: Path):
    audio = write_wav(tmp_path / "warn.wav", duration=3.0, freqs=(220.0,), kick=False)
    result = _run_binary(
        keybpm_binary,
        ["--json", str(audio)],
        {"KEY_BPM_FAKE_MODE": "warn"},
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["key"] == "A minor"
    assert "UserWarning" in result.stderr
    assert "UserWarning" not in result.stdout


@pytest.mark.requires_binary
def test_missing_file_has_single_error_prefix(keybpm_binary: Path):
    result = _run_binary(keybpm_binary, ["does/not/exist.wav"])
    assert result.returncode == 1
    lines = [line for line in result.stderr.splitlines() if line.startswith("Error:")]
    assert lines == ["Error: Audio file does not exist: does/not/exist.wav"]
    assert result.stderr.count("Error:") == 1


@pytest.mark.requires_binary
def test_directory_is_rejected(keybpm_binary: Path, tmp_path: Path):
    result = _run_binary(keybpm_binary, [str(tmp_path)])
    assert result.returncode == 1
    assert result.stderr.count("Error:") == 1
    assert "directory" in result.stderr


@pytest.mark.requires_binary
def test_empty_file_is_rejected(keybpm_binary: Path, tmp_path: Path):
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    result = _run_binary(keybpm_binary, [str(empty)])
    assert result.returncode == 1
    assert "empty" in result.stderr
    assert result.stderr.count("Error:") == 1


@pytest.mark.requires_binary
def test_stub_failure_has_single_error_prefix(keybpm_binary: Path, tmp_path: Path):
    audio = write_wav(tmp_path / "fail.wav", duration=3.0, freqs=(220.0,), kick=False)
    result = _run_binary(
        keybpm_binary,
        [str(audio)],
        {"KEY_BPM_FAKE_MODE": "fail"},
    )
    assert result.returncode == 1
    assert result.stderr.count("Error:") == 1
    assert "synthetic failure from stub" in result.stderr
    assert "Error: Error:" not in result.stderr


@pytest.mark.requires_binary
def test_timeout_kills_sleeping_child(keybpm_binary: Path, tmp_path: Path):
    audio = write_wav(tmp_path / "sleep.wav", duration=3.0, freqs=(220.0,), kick=False)
    started = time.monotonic()
    result = _run_binary(
        keybpm_binary,
        ["--json", str(audio)],
        {
            "KEY_BPM_FAKE_MODE": "sleep",
            "KEY_BPM_FAKE_SLEEP": "30",
            "KEY_BPM_TIMEOUT_SEC": "1",
        },
        timeout=20.0,
    )
    elapsed = time.monotonic() - started
    assert result.returncode == 1
    assert "timed out" in result.stderr
    assert elapsed < 10.0


@pytest.mark.requires_binary
def test_verbose_json_still_parses(keybpm_binary: Path, tmp_path: Path):
    audio = write_wav(tmp_path / "verbose.wav", duration=3.0, freqs=(220.0,), kick=False)
    result = _run_binary(
        keybpm_binary,
        ["-v", "--json", str(audio)],
        {"KEYBPM_DEBUG": "1"},
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["key"] == "A minor"
    assert "Using Python:" in result.stderr
    assert "Using bridge:" in result.stderr


@pytest.mark.requires_binary
def test_decoy_cwd_script_is_ignored(keybpm_binary: Path, tmp_path: Path):
    audio = write_wav(tmp_path / "decoy.wav", duration=3.0, freqs=(220.0,), kick=False)
    work = tmp_path / "work"
    (work / "scripts").mkdir(parents=True)
    (work / "scripts" / "PyBridge.py").write_text(
        "raise SystemExit('decoy script was used')\n",
        encoding="utf-8",
    )

    boxed = tmp_path / "boxed"
    boxed.mkdir()
    boxed_binary = boxed / "Key-BpmFinder"
    shutil.copy2(keybpm_binary, boxed_binary)
    boxed_binary.chmod(0o755)
    shutil.copy2(FAKE_PYTHON, boxed / "PyBridge.py")

    env = os.environ.copy()
    env.update(
        {
            "KEY_BPM_PYTHON": sys.executable,
            "KEY_BPM_FAKE_MODE": "json",
        }
    )
    env.pop("KEY_BPM_BRIDGE", None)

    result = subprocess.run(
        [str(boxed_binary), "--json", str(audio)],
        check=False,
        capture_output=True,
        text=True,
        timeout=15.0,
        cwd=str(work),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["key"] == "A minor"
    assert "decoy script was used" not in result.stderr


@pytest.mark.requires_binary
def test_install_layout_discovery(keybpm_binary: Path, tmp_path: Path):
    audio = write_wav(tmp_path / "installed.wav", duration=3.0, freqs=(220.0,), kick=False)
    prefix = tmp_path / "prefix"
    (prefix / "bin").mkdir(parents=True)
    (prefix / "share" / "keybpm").mkdir(parents=True)
    installed_binary = prefix / "bin" / "Key-BpmFinder"
    shutil.copy2(keybpm_binary, installed_binary)
    installed_binary.chmod(0o755)
    shutil.copy2(FAKE_PYTHON, prefix / "share" / "keybpm" / "PyBridge.py")

    env = os.environ.copy()
    env.update({"KEY_BPM_PYTHON": sys.executable, "KEY_BPM_FAKE_MODE": "json"})
    env.pop("KEY_BPM_BRIDGE", None)

    result = subprocess.run(
        [str(installed_binary), "--json", str(audio)],
        check=False,
        capture_output=True,
        text=True,
        timeout=15.0,
        cwd=str(tmp_path),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["key"] == "A minor"


@pytest.mark.requires_binary
def test_sigint_forwards_to_child(keybpm_binary: Path, tmp_path: Path):
    audio = write_wav(tmp_path / "sigint.wav", duration=3.0, freqs=(220.0,), kick=False)
    env = _stub_env(
        {
            "KEY_BPM_FAKE_MODE": "sleep",
            "KEY_BPM_FAKE_SLEEP": "20",
            "KEY_BPM_TIMEOUT_SEC": "15",
        }
    )
    proc = subprocess.Popen(
        [str(keybpm_binary), "--json", str(audio)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    time.sleep(0.4)
    proc.send_signal(signal.SIGINT)
    try:
        _stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise
    assert proc.returncode != 0
    assert (
        "timed out" in stderr
        or "signal" in stderr
        or proc.returncode in (1, 130, -signal.SIGINT)
    )
