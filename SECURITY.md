# Security Policy

## Reporting a vulnerability

If you discover a security issue — for example a way to leak configured API keys, extract
sealed benchmark content, or execute unintended commands through the evaluation tooling —
please report it privately rather than opening a public issue.

Email the maintainer at **fl.sean03@gmail.com** with a description and reproduction steps.
You can expect an acknowledgment within a few days.

## Handling of secrets

This project keeps all credentials **out of the repository**. Local configuration files that
contain secrets (e.g. judge API keys used by the grading tooling) are git-ignored and stored
off-repo.

Sealed benchmark content — reference answers, tolerances, grading keys, canary tokens, and
the held-out task set — lives in a separate private store and must never enter this
repository; CI scans for it.

Never commit a real API key, token, or credential. If one is committed by accident, treat it
as compromised: rotate the key and scrub it from history.
