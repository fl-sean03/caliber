# Security Policy

## Reporting a vulnerability

If you discover a security issue — for example a way to leak configured API keys or execute
unintended commands through the agent — please report it privately rather than opening a
public issue.

Email the maintainer at **fl.sean03@gmail.com** with a description and reproduction steps.
You can expect an acknowledgment within a few days.

## Handling of secrets

This project keeps all credentials **out of the repository**. Local configuration files that
contain secrets are git-ignored and distributed only as `.example` templates:

- `config.yaml` (← `config.example.yaml`)
- `.claude/settings.json` (← `.claude/settings.json.example`)
- `.mcp.json` (← `.mcp.json.example`)

Never commit a real API key, token, or credential. If one is committed by accident, treat it
as compromised: rotate the key and scrub it from history.
