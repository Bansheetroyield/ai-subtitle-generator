"""Watch-folder handler — auto-caption new media as it lands.

Polls a directory (no inotify on Windows) and dispatches each stable
new file through the pipeline. Stability is defined as "size unchanged
for two consecutive polls."
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from ai_subtitle_generator.core.pipeline import PipelineRequest, run_pipeline
from ai_subtitle_generator.core.registry import HostRegistries

log = logging.getLogger(__name__)

_MEDIA_EXTS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".mp3", ".wav", ".m4a", ".flac"}


@dataclass(slots=True)
class WatchState:
    seen: dict[Path, int] = field(default_factory=dict)   # path -> last size
    done: set[Path] = field(default_factory=set)


def _is_stable(path: Path, state: WatchState) -> bool:
    try:
        size = path.stat().st_size
    except OSError:
        return False
    prev = state.seen.get(path)
    state.seen[path] = size
    return prev is not None and prev == size and size > 0


def _candidates(root: Path) -> Iterable[Path]:
    for p in root.iterdir():
        if p.is_file() and p.suffix.lower() in _MEDIA_EXTS:
            yield p


def watch(
    folder: Path,
    registries: HostRegistries,
    *,
    poll_seconds: float = 2.0,
    stop_after: int | None = None,
) -> list[Path]:
    """Block and caption new media in `folder`. Returns paths processed."""
    state = WatchState()
    processed: list[Path] = []
    log.info("watching %s (poll=%.1fs)", folder, poll_seconds)

    while True:
        for candidate in _candidates(folder):
            if candidate in state.done:
                continue
            if not _is_stable(candidate, state):
                continue
            try:
                run_pipeline(PipelineRequest(media_path=candidate), registries)
                state.done.add(candidate)
                processed.append(candidate)
                log.info("captioned %s", candidate.name)
            except Exception as exc:  # noqa: BLE001
                log.error("failed to caption %s: %s", candidate.name, exc)
                state.done.add(candidate)
            if stop_after is not None and len(processed) >= stop_after:
                return processed
        time.sleep(poll_seconds)