"""In-memory run store with event history and live-event wakeups.

v1 keeps runs in process memory: no queue, cache, or database is introduced.
History is bounded per run so a reconnecting client can reload state without
depending on missed SSE messages.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone

from .models import RunEvent, RunRecord, event_level

MAX_EVENTS_PER_RUN = 500
MAX_RUNS = 200


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, RunRecord] = {}
        self._order: list[str] = []
        self._signals: dict[str, asyncio.Event] = {}
        self._signal_loops: dict[str, asyncio.AbstractEventLoop] = {}

    def create(self, record: RunRecord) -> RunRecord:
        with self._lock:
            self._runs[record.run_id] = record
            self._order.append(record.run_id)
            while len(self._order) > MAX_RUNS:
                oldest = self._order.pop(0)
                self._runs.pop(oldest, None)
                self._signals.pop(oldest, None)
        return record

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def list_recent(self, limit: int = 20) -> list[RunRecord]:
        with self._lock:
            ids = list(reversed(self._order[-limit:]))
            return [self._runs[run_id] for run_id in ids if run_id in self._runs]

    def update(self, run_id: str, **fields: object) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = _utcnow()
            return record

    def append_event(
        self,
        run_id: str,
        event: str,
        data: dict | None = None,
        candidate_id: str | None = None,
    ) -> RunEvent | None:
        payload = dict(data or {})
        entry = RunEvent(
            timestamp=_utcnow(),
            level=event_level(event, payload),
            event=event,
            run_id=run_id,
            candidate_id=candidate_id,
            data=payload,
        )
        loop = _running_loop()
        with self._lock:
            record = self._runs.get(run_id)
            if record is None:
                return None
            record.events.append(entry)
            if len(record.events) > MAX_EVENTS_PER_RUN:
                del record.events[: len(record.events) - MAX_EVENTS_PER_RUN]
            record.updated_at = entry.timestamp
            signal = self._signals.get(run_id)
        if signal is not None and loop is not None:
            loop.call_soon_threadsafe(signal.set)
        return entry

    def event_signal(self, run_id: str) -> asyncio.Event:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        with self._lock:
            signal = self._signals.get(run_id)
            if signal is None or (loop is not None and self._signal_loops.get(run_id) is not loop):
                signal = asyncio.Event()
                self._signals[run_id] = signal
                if loop is not None:
                    self._signal_loops[run_id] = loop
            return signal

    async def wait_for_event_index(
        self, run_id: str, last_index: int, timeout: float = 15.0
    ) -> int:
        signal = self.event_signal(run_id)
        signal.clear()
        try:
            await asyncio.wait_for(signal.wait(), timeout)
        except TimeoutError:
            pass
        record = self.get(run_id)
        return len(record.events) if record else last_index


def _running_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None
