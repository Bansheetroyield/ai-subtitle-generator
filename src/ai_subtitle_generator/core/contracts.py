"""Shared plugin contracts.

Every extension module — transcriber, translator, formatter, exporter —
implements one of these Protocols. The host never imports a concrete
plugin; it only ever sees these shapes. This is the seam that keeps the
plugin host honest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class Word:
    """A single timed token from an ASR backend."""
    text: str
    start_ms: int
    end_ms: int
    confidence: float = 1.0


@dataclass(slots=True)
class Segment:
    """A caption segment: one on-screen subtitle."""
    start_ms: int
    end_ms: int
    text: str
    words: list[Word] = field(default_factory=list)
    speaker: str | None = None


@dataclass(slots=True, frozen=True)
class MediaRef:
    """Opaque handle to a media file the host already demuxed."""
    path: Path
    duration_ms: int
    sample_rate: int
    channels: int


@runtime_checkable
class TranscriberPlugin(Protocol):
    """Turns audio into timed segments."""

    name: str
    version: str

    def transcribe(
        self,
        media: MediaRef,
        *,
        language: str | None = None,
        word_timestamps: bool = True,
    ) -> list[Segment]: ...


@runtime_checkable
class TranslatorPlugin(Protocol):
    """Rewrites segment text into a target language, preserving timing."""

    name: str
    version: str

    def translate(self, segments: list[Segment], target_lang: str) -> list[Segment]: ...


@runtime_checkable
class FormatterPlugin(Protocol):
    """Serializes segments into a caption file format."""

    name: str
    extension: str

    def format(self, segments: list[Segment], *, line_max_chars: int = 42) -> str: ...


@runtime_checkable
class ExporterPlugin(Protocol):
    """Writes formatted captions to disk, possibly sidecar to media."""

    name: str

    def export(self, payload: str, target: Path) -> Path: ...