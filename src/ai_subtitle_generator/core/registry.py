"""Plugin registry — the runtime catalog of loaded extensions.

The registry is populated by `loader.py`. It maps plugin names to
instances and enforces that only one plugin per name is active. Lookups
are O(1); iteration order preserves load order for deterministic CLI
output.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any, Generic, TypeVar

from ai_subtitle_generator.core.contracts import (
    ExporterPlugin,
    FormatterPlugin,
    TranscriberPlugin,
    TranslatorPlugin,
)

log = logging.getLogger(__name__)

T = TypeVar("T")


class PluginRegistry(Generic[T]):
    """Name-keyed registry. Insertion-ordered. Rejects duplicates."""

    __slots__ = ("_kind", "_items")

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._items: OrderedDict[str, T] = OrderedDict()

    def register(self, name: str, plugin: T) -> None:
        if name in self._items:
            log.warning("plugin %r already registered in %s; skipping", name, self._kind)
            return
        self._items[name] = plugin
        log.debug("registered %s plugin %r", self._kind, name)

    def get(self, name: str) -> T:
        try:
            return self._items[name]
        except KeyError as exc:
            available = ", ".join(self._items) or "<none>"
            raise KeyError(f"no {self._kind} plugin named {name!r}; have: {available}") from exc

    def first(self) -> T | None:
        return next(iter(self._items.values()), None)

    def names(self) -> list[str]:
        return list(self._items)

    def __contains__(self, name: object) -> bool:
        return name in self._items

    def __len__(self) -> int:
        return len(self._items)


class HostRegistries:
    """Bundle of every registry the host needs, in one object."""

    __slots__ = ("transcribers", "translators", "formatters", "exporters")

    def __init__(self) -> None:
        self.transcribers: PluginRegistry[TranscriberPlugin] = PluginRegistry("transcriber")
        self.translators: PluginRegistry[TranslatorPlugin] = PluginRegistry("translator")
        self.formatters: PluginRegistry[FormatterPlugin] = PluginRegistry("formatter")
        self.exporters: PluginRegistry[ExporterPlugin] = PluginRegistry("exporter")

    def summary(self) -> dict[str, list[str]]:
        return {
            "transcribers": self.transcribers.names(),
            "translators": self.translators.names(),
            "formatters": self.formatters.names(),
            "exporters": self.exporters.names(),
        }


def _unused(_: Any) -> None:  # pragma: no cover - keeps imports honest
    return None