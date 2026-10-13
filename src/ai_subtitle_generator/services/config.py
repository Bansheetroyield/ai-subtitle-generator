"""Config service — layered TOML loading with env overrides.

Precedence (low to high):
    config/default.toml  <  config/local.toml  <  AISUB_* env vars
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT = _REPO_ROOT / "config" / "default.toml"
_LOCAL = _REPO_ROOT / "config" / "local.toml"

_ENV_PREFIX = "AISUB_"


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _env_overrides() -> dict[str, Any]:
    """AISUB_SECTION__KEY=value -> {"section": {"key": value}}"""
    out: dict[str, Any] = {}
    for key, value in os.environ.items():
        if not key.startswith(_ENV_PREFIX):
            continue
        tail = key[len(_ENV_PREFIX):].lower()
        parts = tail.split("__")
        cursor = out
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = _coerce(value)
    return out


def _coerce(value: str) -> Any:
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def load_config() -> dict[str, Any]:
    """Return the fully merged runtime config dict."""
    cfg: dict[str, Any] = {}
    if _DEFAULT.exists():
        with _DEFAULT.open("rb") as fh:
            cfg = tomllib.load(fh)
    if _LOCAL.exists():
        with _LOCAL.open("rb") as fh:
            cfg = _deep_merge(cfg, tomllib.load(fh))
    return _deep_merge(cfg, _env_overrides())