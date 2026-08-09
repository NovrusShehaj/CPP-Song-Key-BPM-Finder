#!/usr/bin/env bash
# End-to-end check: run the built binary against the bundled sample and
# verify it reports the expected key. Requires the project to already be
# built (see README) and KEY_BPM_PYTHON to point at a Python with the
# dependencies from requirements.txt installed.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
binary="${repo_root}/build/Key-BpmFinder"
sample="${repo_root}/samples/test-tone-a-minor-120bpm.wav"

if [[ ! -x "${binary}" ]]; then
  echo "Binary not found at ${binary}; build the project first." >&2
  exit 1
fi

output="$("${binary}" --json "${sample}")"
echo "${output}"

if ! grep -q '"key": "A minor"' <<<"${output}"; then
  echo "Expected key 'A minor' in output, got: ${output}" >&2
  exit 1
fi

echo "Integration test passed."
