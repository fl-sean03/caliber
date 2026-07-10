# harnesses/

Each model is benchmarked through its **own native harness**, recorded in every run's
`harness:{name,version,config_hash}` provenance field so results stay comparable and the
measurement path adds no custom orchestration.

- **`native-claude/`** — Claude Code native session-holder (`asw_native.py`): holds one
  `claude -p --input-format stream-json` session per task with stdin open; background-task
  completion natively re-wakes the worker. See `native-claude/RUNNER.md`.
- *(future)* `native-codex/`, others — added as new models/vendors are benchmarked.

Harnesses are versioned; improvements land as new versions here, and each run records which
version produced it.
