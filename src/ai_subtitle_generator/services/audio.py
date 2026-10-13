"""Audio I/O service — media probing and 16 kHz mono extraction.

Uses ffmpeg via subprocess for demux (no PyAV dependency, keeps the
install light). Whisper-family backends expect 16 kHz mono float32;
this module guarantees that contract regardless of source format.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from ai_subtitle_generator.core.contracts import MediaRef

log = logging.getLogger(__name__)

TARGET_SR = 16_000
_FFMPEG = shutil.which("ffmpeg")
_FFPROBE = shutil.which("ffprobe")


class AudioError(RuntimeError):
    """Raised when ffmpeg/ffprobe is missing or media cannot be decoded."""


def _require_ffmpeg() -> None:
    if not _FFMPEG or not _FFPROBE:
        raise AudioError(
            "ffmpeg/ffprobe not found on PATH. Install from https://ffmpeg.org "
            "or place binaries next to the executable."
        )


def probe_media(path: Path) -> MediaRef:
    """Return a MediaRef with duration and channel layout."""
    _require_ffmpeg()
    assert _FFPROBE is not None
    cmd = [
        _FFPROBE, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    duration_s = float(out.stdout.strip() or "0")
    return MediaRef(
        path=path,
        duration_ms=int(duration_s * 1000),
        sample_rate=TARGET_SR,
        channels=1,
    )


def extract_mono16k(path: Path) -> np.ndarray:
    """Decode `path` to a 1-D float32 array at 16 kHz."""
    _require_ffmpeg()
    assert _FFMPEG is not None
    with tempfile.TemporaryDirectory(prefix="aisub-") as tmp:
        wav = Path(tmp) / "audio.wav"
        cmd = [
            _FFMPEG, "-nostdin", "-y",
            "-i", str(path),
            "-vn",
            "-ac", "1",
            "-ar", str(TARGET_SR),
            "-f", "wav",
            str(wav),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        data, sr = sf.read(wav, dtype="float32", always_2d=False)
    if sr != TARGET_SR:
        raise AudioError(f"resample failed: got {sr} Hz, expected {TARGET_SR}")
    return np.asarray(data, dtype=np.float32)