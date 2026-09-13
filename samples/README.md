# Audio fixtures

This repository may include a checked-in development tone at
`samples/test-tone-a-minor-120bpm.wav`. Tests do **not** require that file.

Automated tests synthesize short, copyright-free WAV fixtures with
`tests/generate_fixture.py` and write them to `tests/.generated/` (gitignored).

Generate the default A-minor / 120 BPM fixture:

```bash
python3 tests/generate_fixture.py --name K1 --output tests/.generated/test-tone-a-minor-120bpm.wav
```

| ID | Contents | Expected key | Expected BPM |
|---|---|---|---|
| K1 | A-minor triad + 120 BPM kicks | A minor | 120 ± 2 |
| K2 | G-major triad + 100 BPM | G major | 100 ± 2 |
| K3 | C-major triad + 140 BPM | C major | 140 ± 2 |
| K4 | Kick-only 174 BPM | not required | 174 ± 3 after octave fold |
| K5 | Kick-only 70 BPM | not required | 70 ± 3 after octave fold |
