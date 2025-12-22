from __future__ import annotations

from dataclasses import dataclass, field

from cachetools import TTLCache

from app.schemas import AnalyzePageResponse, Difficulty


@dataclass
class SessionState:
    difficulty: Difficulty = Difficulty.beginner
    page: AnalyzePageResponse | None = None
    turns: list[dict] = field(default_factory=list)  # [{"role": "user"/"assistant", "text": "..."}]


class SessionStore:
    def __init__(self, *, maxsize: int = 10_000, ttl_seconds: int = 60 * 60) -> None:
        self._cache: TTLCache[str, SessionState] = TTLCache(maxsize=maxsize, ttl=ttl_seconds)

    def get_or_create(self, session_id: str) -> SessionState:
        state = self._cache.get(session_id)
        if state is None:
            state = SessionState()
            self._cache[session_id] = state
        return state

    def set_page(self, session_id: str, page: AnalyzePageResponse) -> SessionState:
        state = self.get_or_create(session_id)
        state.page = page
        return state

    def append_turn(self, session_id: str, role: str, text: str, *, max_turns: int = 12) -> SessionState:
        state = self.get_or_create(session_id)
        state.turns.append({"role": role, "text": text})
        if len(state.turns) > max_turns:
            state.turns = state.turns[-max_turns:]
        return state


