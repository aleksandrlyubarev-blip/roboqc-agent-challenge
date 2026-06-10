"""
Tiny in-memory TTL cache for repeated reasoning requests.

Cloud Run instances are ephemeral and may run several at once, so this is a
best-effort, per-instance optimization (identical defect batches re-analyzed
within minutes — e.g. dashboard refreshes). Swap for Memorystore if cross-
instance sharing ever pays for itself; the interface is deliberately minimal
to keep that swap cheap.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict


class TTLCache:
    """LRU + TTL cache mapping request fingerprints to serialized results."""

    def __init__(self, max_entries: int = 256, ttl_seconds: float = 300.0) -> None:
        self._max_entries = max_entries
        self._ttl = ttl_seconds
        self._entries: OrderedDict[str, tuple[float, str]] = OrderedDict()

    @staticmethod
    def fingerprint(operation: str, payload: dict[str, object]) -> str:
        """Deterministic key for an (operation, payload) pair."""

        raw = json.dumps({"op": operation, "payload": payload}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> str | None:
        """Return the cached value or None if absent/expired."""

        entry = self._entries.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return value

    def put(self, key: str, value: str) -> None:
        """Insert a value, evicting the least-recently-used entry if full."""

        self._entries[key] = (time.monotonic() + self._ttl, value)
        self._entries.move_to_end(key)
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def __len__(self) -> int:
        return len(self._entries)
