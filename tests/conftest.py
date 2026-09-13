"""Shared pytest fixtures and binary discovery."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from generate_fixture import write_named_fixture

ROOT = Path(__file__).resolve().parents[1]
GENERATED = Path(__file__).resolve().parent / ".generated"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "requires_binary: needs the Key-BpmFinder executable")


def project_root() -> Path:
    return ROOT


def find_keybpm_binary() -> Path | None:
    configured = os.environ.get("KEY_BPM_BINARY")
    if configured:
        path = Path(configured)
        if path.is_file() and os.access(path, os.X_OK):
            return path
        return None
    for candidate in (
        ROOT / "build" / "Key-BpmFinder",
        ROOT / ".tmp" / "build" / "Key-BpmFinder",
        ROOT / ".tmp" / "prefix" / "bin" / "Key-BpmFinder",
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


@pytest.fixture(scope="session")
def generated_dir() -> Path:
    GENERATED.mkdir(parents=True, exist_ok=True)
    return GENERATED


@pytest.fixture(scope="session")
def am_120_wav(generated_dir: Path) -> Path:
    path = generated_dir / "test-tone-a-minor-120bpm.wav"
    write_named_fixture(path, "K1")
    os.environ.setdefault("KEY_BPM_SAMPLE", str(path))
    return path


@pytest.fixture(scope="session")
def keybpm_binary() -> Path:
    binary = find_keybpm_binary()
    if binary is None:
        pytest.skip("Key-BpmFinder binary is not built")
    return binary
