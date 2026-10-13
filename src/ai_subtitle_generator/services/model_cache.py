"""Model weight cache — content-addressed, disk-backed, LRU evicted.

Transcription backends ask for weights by (name, revision). We hash the
key, look up a manifest, and hand back a local path — downloading from
the configured mirror if absent. Eviction keeps total cache under the
configured ceiling (default 12 GB).
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_CEILING_BYTES = 12 * 1024**3


@dataclass(slots=True, frozen=True)
class CacheEntry:
    key: str
    path: Path
    size_bytes: int
    last