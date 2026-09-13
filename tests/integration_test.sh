#!/usr/bin/env bash
# End-to-end check: run the built binary against a generated A-minor 120 BPM
# fixture and json.loads the stdout payload.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
binary="${KEY_BPM_BINARY:-${repo_root}/build/Key-BpmFinder}"
python_bin="${KEY_BPM_PYTHON:-python3}"

if [[ ! -x "${binary}" ]]; then
  echo "Binary not found at ${binary}; build the project first or set KEY_BPM_BINARY." >&2
  exit 1
fi

sample="${KEY_BPM_SAMPLE:-}"
if [[ -z "${sample}" || ! -f "${sample}" ]]; then
  generated_dir="${repo_root}/tests/.generated"
  mkdir -p "${generated_dir}"
  sample="${generated_dir}/test-tone-a-minor-120bpm.wav"
  "${python_bin}" "${repo_root}/tests/generate_fixture.py" --name K1 --output "${sample}"
fi

output="$("${binary}" --json "${sample}")"
printf '%s\n' "${output}"

"${python_bin}" - "${output}" <<'PY'
import json
import sys

raw = sys.argv[1]
try:
    payload = json.loads(raw)
except json.JSONDecodeError as exc:
    raise SystemExit(f"stdout was not valid JSON: {exc}: {raw!r}") from exc

if not raw.lstrip().startswith("{"):
    raise SystemExit(f"JSON stdout must start with '{{': {raw!r}")

if payload.get("key") != "A minor":
    raise SystemExit(f"Expected key 'A minor', got {payload.get('key')!r}")

bpm = float(payload["bpm"])
if bpm < 117 or bpm > 123:
    raise SystemExit(f"Expected BPM in [117, 123], got {bpm}")

if int(payload.get("analysis_sample_rate", 0)) != 22050:
    raise SystemExit(
        f"Expected analysis_sample_rate 22050, got {payload.get('analysis_sample_rate')!r}"
    )
PY

# Flag-order and help contract checks that do not need librosa when using the real sample.
help_out="$("${binary}" --help)"
if ! grep -q "Usage:" <<<"${help_out}"; then
  echo "Expected --help to print usage." >&2
  exit 1
fi

version_out="$("${binary}" --version)"
if ! grep -q "0.1.0" <<<"${version_out}"; then
  echo "Expected --version to include 0.1.0, got: ${version_out}" >&2
  exit 1
fi

json_after="$("${binary}" "${sample}" --json)"
"${python_bin}" -c 'import json,sys; json.loads(sys.argv[1])' "${json_after}"

echo "Integration test passed."
