"""Plugin loader — discovers and instantiates extension modules.

Two discovery paths:

1. Entry points declared under `ai_subtitle_generator.plugins` in any
   installed package (see pyproject.toml).
2. Filesystem scan of configured `plugins/` roots, each subfolder with
   a `plugin.toml` manifest.

Manifests are validated before import. A plugin whose manifest is
malformed is skipped with a warning — the host never crashes on a bad
extension.
"""

from __future__ import annotations

import importlib
import importlib.metadata as md
import logging
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_subtitle_generator.core.contracts import (
    ExporterPlugin,
    FormatterPlugin,
    TranscriberPlugin,
    TranslatorPlugin,
)
from ai_subtitle_generator.core.registry import HostRegistries

log = logging.getLogger(__name__)

_VALID_KINDS = {"transcriber", "translator", "formatter", "exporter"}


@dataclass(slots=True, frozen=True)
class PluginManifest:
    name: str
    kind: str
    version: str
    entry: str          # "module.path:ClassName"
    description: str = ""
    requires: tuple[str, ...] = ()


def parse_manifest(path: Path) -> PluginManifest:
    """Read and validate a plugin.toml. Raises ValueError on bad shape."""
    with path.open("rb") as fh:
        raw: dict[str, Any] = tomllib.load(fh)
    try:
        name = str(raw["name"])
        kind = str(raw["kind"])
        version = str(raw["version"])
        entry = str(raw["entry"])
    except KeyError as exc:
        raise ValueError(f"{path}: missing required key {exc.args[0]!r}") from exc
    if kind not in _VALID_KINDS:
        raise ValueError(f"{path}: unknown kind {kind!r}; expected one of {sorted(_VALID_KINDS)}")
    if ":" not in entry:
        raise ValueError(f"{path}: entry must be 'module:Class', got {entry!r}")
    return PluginManifest(
        name=name,
        kind=kind,
        version=version,
        entry=entry,
        description=str(raw.get("description", "")),
        requires=tuple(raw.get("requires", ())),
    )


def _instantiate(manifest: PluginManifest) -> object:
    module_path, _, class_name = manifest.entry.partition(":")
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    return cls()


def _register(registries: HostRegistries, manifest: PluginManifest, instance: object) -> None:
    match manifest.kind:
        case "transcriber":
            if not isinstance(instance, TranscriberPlugin):
                raise TypeError(f"{manifest.name}: does not satisfy TranscriberPlugin")
            registries.transcribers.register(manifest.name, instance)
        case "translator":
            if not isinstance(instance, TranslatorPlugin):
                raise TypeError(f"{manifest.name}: does not satisfy TranslatorPlugin")
            registries.translators.register(manifest.name, instance)
        case "formatter":
            if not isinstance(instance, FormatterPlugin):
                raise TypeError(f"{manifest.name}: does not satisfy FormatterPlugin")
            registries.formatters.register(manifest.name, instance)
        case "exporter":
            if not isinstance(instance, ExporterPlugin):
                raise TypeError(f"{manifest.name}: does not satisfy ExporterPlugin")
            registries.exporters.register(manifest.name, instance)
        case _:
            raise ValueError(f"unreachable kind {manifest.kind!r}")


def load_from_filesystem(registries: HostRegistries, roots: list[Path]) -> int:
    """Scan roots for `*/plugin.toml` and load each. Returns count loaded."""
    loaded = 0
    for root in roots:
        if not root.is_dir():
            log.debug("plugin root %s does not exist; skipping", root)
            continue
        for manifest_path in sorted(root.rglob("plugin.toml")):
            try:
                manifest = parse_manifest(manifest_path)
                instance = _instantiate(manifest)
                _register(registries, manifest, instance)
                loaded += 1
            except Exception as exc:  # noqa: BLE001 - plugin isolation is the point
                log.warning("skipping plugin at %s: %s", manifest_path, exc)
    return loaded


def load_from_entrypoints(registries: HostRegistries) -> int:
    """Load plugins declared via the `ai_subtitle_generator.plugins` group."""
    loaded = 0
    eps = md.entry_points(group="ai_subtitle_generator.plugins")
    for ep in eps:
        try:
            instance = ep.load()()
            kind = getattr(instance, "kind", None) or _infer_kind(instance)
            manifest = PluginManifest(
                name=ep.name,
                kind=kind,
                version=getattr(instance, "version", "0.0.0"),
                entry=ep.value,
            )
            _register(registries, manifest, instance)
            loaded += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("skipping entry-point plugin %s: %s", ep.name, exc)
    return loaded


def _infer_kind(instance: object) -> str:
    if isinstance(instance, TranscriberPlugin):
        return "transcriber"
    if isinstance(instance, TranslatorPlugin):
        return "translator"
    if isinstance(instance, FormatterPlugin):
        return "formatter"
    if isinstance(instance, ExporterPlugin):
        return "exporter"
    raise TypeError(f"cannot infer plugin kind for {type(instance).__name__}")


def bootstrap_plugins(roots: list[Path]) -> HostRegistries:
    """Full plugin bootstrap: filesystem scan + entry points, in that order."""
    registries = HostRegistries()
    fs_count = load_from_filesystem(registries, roots)
    ep_count = load_from_entrypoints(registries)
    log.info("plugin bootstrap complete: %d filesystem, %d entry-point", fs_count, ep_count)
    if not registries.transcribers:
        log.warning("no transcriber plugins loaded — captions cannot be generated")
    return registries


def _ensure_plugins_importable(repo_root: Path) -> None:
    """Make `plugins/` importable when running from a source checkout."""
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))