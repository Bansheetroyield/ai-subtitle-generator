# Contributing to ai-subtitle-generator

Thanks for wanting to help caption the world. This repo is a **plugin-host** architecture: a small Python core that loads transcription backends, translation backends, and caption formatters as extension modules at runtime.

## Ground rules

- Python 3.11+ is the target. We use `pyproject.toml` (PEP 621) and `hatchling`.
- Native extensions (C++ VAD, C# SAPI bridge, Java ONNX bridge) live under `native/` and are optional — the core must run without any of them.
- Every plugin must declare a manifest (`plugin.toml`) and implement the abstract contract in `core/contracts.py`.
- Type hints are required on all public functions. `mypy --strict` is enforced in CI.

## Setting up

```bash
git clone https://github.com/<you>/ai-subtitle-generator
cd ai-subtitle-generator
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,whisper,faster-whisper]"
python -m ai_subtitle_generator --list-plugins
```

## Adding a plugin

1. Create a folder under `plugins/<category>/<your_plugin>/`.
2. Drop in `plugin.toml` (see `plugins/transcribers/whisper_faster/plugin.toml` for a template).
3. Implement the contract from `core/contracts.py` in `__init__.py`.
4. Register it in your local `config/plugins.toml` or let autodiscovery find it.
5. Add a test under `tests/plugins/`.

## Style

- `ruff` for lint, `black` for format, `isort` for imports. Run `make lint` before pushing.
- Commit messages: `feat(transcribers): add vosk backend`, `fix(formatters): handle CRLF in SRT`.
- Keep PRs scoped. One plugin or one fix per PR.

## Reporting bugs

Open an issue with: OS build, Python version, `python -m ai_subtitle_generator --diagnostics` output, and a minimal media sample if the bug is timing-related.