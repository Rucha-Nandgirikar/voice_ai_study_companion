from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class SelectedTopics:
    url: str
    topics: list[str]
    updated_at: float


class TopicSelectionStore:
    """
    MVP in-memory store for selected topics keyed by URL.
    NOTE: Cloud Run instances can restart; for persistence, move to Postgres later.
    """

    def __init__(self, ttl_seconds: int = 60 * 60 * 24 * 7):
        self._ttl = int(ttl_seconds)
        self._by_url: dict[str, SelectedTopics] = {}

    def _now(self) -> float:
        return time.time()

    def _gc(self) -> None:
        cutoff = self._now() - self._ttl
        dead = [u for u, rec in self._by_url.items() if rec.updated_at < cutoff]
        for u in dead:
            self._by_url.pop(u, None)

    def set(self, url: str, topics: list[str]) -> SelectedTopics:
        self._gc()
        rec = SelectedTopics(url=url, topics=topics, updated_at=self._now())
        self._by_url[url] = rec
        return rec

    def get(self, url: str) -> SelectedTopics | None:
        self._gc()
        rec = self._by_url.get(url)
        if not rec:
            return None
        if rec.updated_at < (self._now() - self._ttl):
            self._by_url.pop(url, None)
            return None
        return rec


