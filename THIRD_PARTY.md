# Third-party licenses

First-party code in this repository is MIT-licensed. See [LICENSE](LICENSE).

The analyzer runtime is a Python process. Installing `requirements.txt` or
`requirements.lock` pulls additional wheels (typically `librosa`, `numpy`,
`soundfile` / libsndfile, `scipy`, `numba`, and their dependencies). Those
packages have their own licenses (commonly BSD or MIT, and some more complex
terms).

This file is **not** a complete license inventory of every transitive wheel.
If you distribute a built environment, run `pip freeze` in that environment and
comply with each package's license. The supported v0.x distribution model is
source plus a local virtualenv, not a bundled interpreter.
