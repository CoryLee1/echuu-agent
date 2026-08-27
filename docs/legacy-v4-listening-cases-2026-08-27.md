# Legacy V4 listening cases (2026-08-27)

These three compact fixtures preserve the inputs used for the pre-refactor V4
listening pass. They are intentionally committed without WAV files so the
repository does not absorb roughly 37 MB of generated audio.

The local reference run used commit `f0d4260`, Qwen chat generation, the
`Cherry` voice, and produced 24 kHz / 16-bit / mono WAV files. Approximate
durations were 243 s, 301 s, and 255 s respectively.

The canonical inputs live in `echuu/eval/legacy_v4_cases.jsonl`. Future
three-way comparisons must reuse the same model, character, topic, and seed for
`legacy_v4`, `refactor_no_dossier`, and `refactor_full`.
