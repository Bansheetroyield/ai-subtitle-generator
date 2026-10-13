"""Caption pipeline — the host's orchestration layer.

Given a media path and a set of resolved plugins, this walks:
    demux -> transcribe -> (translate) -> format -> export

Each stage is a pure function over the shared `Segment` list, so it's
trivially testable and easy to instrument. Progress is reported through
a callback so the CLI and GUI can both subscribe.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ai_subtitle_generator.core.contracts import MediaRef, Segment
from ai_subtitle_generator.core.registry import HostRegistries
from ai_subtitle_generator.services.audio import probe_media

log = logging.getLogger(__name__)

ProgressFn = Callable[[str, float], None]


@dataclass(slots=True)
class PipelineRequest:
    media_path: Path
    output_path: Path | None = None
    transcriber: str | None = None
    translator: str | None = None
    formatter: str | None = None
    target_language: str | None = None
    line_max_chars: int = 42


@dataclass(slots=True)
class PipelineResult:
    segments: list[Segment]
    output_path: Path
    elapsed_s: float
    backend: str


def _noop_progress(stage: str, frac: float) -> None:  # pragma: no cover
    return None


def run_pipeline(
    request: PipelineRequest,
    registries: HostRegistries,
    *,
    progress: ProgressFn = _noop_progress,
) -> PipelineResult:
    """Execute the full caption pipeline. Raises on unrecoverable errors."""
    started = time.perf_counter()

    progress("probe", 0.0)
    media: MediaRef = probe_media(request.media_path)
    log.info("probed %s: %d ms, %d Hz", media.path.name, media.duration_ms, media.sample_rate)

    transcriber_name = request.transcriber or _default_or_raise(registries, "transcriber")
    transcriber = registries.transcribers.get(transcriber_name)
    progress("transcribe", 0.05)
    segments = transcriber.transcribe(
        media,
        language=request.target_language,
        word_timestamps=True,
    )
    log.info("transcribed %d segments via %s", len(segments), transcriber_name)

    if request.translator and request.target_language:
        translator = registries.translators.get(request.translator)
        progress("translate", 0.7)
        segments = translator.translate(segments, request.target_language)

    formatter_name = request.formatter or _default_or_raise(registries, "formatter")
    formatter = registries.formatters.get(formatter_name)
    progress("format", 0.9)
    payload = formatter.format(segments, line_max_chars=request.line_max_chars)

    output_path = request.output_path or request.media_path.with_suffix(f".{formatter.extension}")
    output_path.write_text(payload, encoding="utf-8")
    progress("export", 1.0)

    elapsed = time.perf_counter() - started
    log.info("pipeline done in %.2fs -> %s", elapsed, output_path)
    return PipelineResult(
        segments=segments,
        output_path=output_path,
        elapsed_s=elapsed,
        backend=transcriber_name,
    )


def _default_or_raise(registries: HostRegistries, kind: str) -> str:
    reg = getattr(registries, f"{kind}s")
    first = reg.first()
    if first is None:
        raise RuntimeError(f"no {kind} plugin available; install one or check config")
    return reg.names()[0]