# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.6.x   | ✅        |
| 0.5.x   | ⚠️ critical fixes only |
| < 0.5   | ❌        |

## Reporting a vulnerability

Email `security@ai-subtitle-generator.dev` (PGP key in `docs/security/pgp.asc`) or open a private security advisory on GitHub.

**Do not** open public issues for: arbitrary code execution via a malicious plugin manifest, path traversal in `exports/` writers, or deserialization flaws in the model cache.

## Threat model

Plugins are **code**, not data. Loading a third-party plugin from an untrusted source is equivalent to running arbitrary Python. The loader validates manifests but does not sandbox plugin bytecode. Only install plugins you trust.

Media parsing (ffmpeg demux, subtitle line parsing) is treated as untrusted input. Fuzz corpora live in `tests/fuzz/`.

## Out of scope

- Captions being wrong (that's a model quality issue, not a security issue).
- Denial of service from very long media files (documented limit: 4h per file).