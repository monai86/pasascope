from __future__ import annotations

import logging
import threading
import weakref
from collections import OrderedDict
from collections.abc import Callable, Iterable, Iterator, MutableMapping
from typing import Any

logger = logging.getLogger("therapist_app_v2.repository")


class LazyTable(MutableMapping):
    """Records of one kind, read from the database when they are first asked for.

    It stands where a plain ``dict`` of every row used to be, and services use
    it the same way: they look a record up by id, change the object they get
    back, and the repository's ``save`` writes what changed.

    That only works if everyone who asks for a record gets the same object, so
    the table is an identity map. Recently used records are held strongly, up
    to ``max_cached``; beyond that a record that matches what the database
    holds is let go, but stays reachable for as long as any caller still has
    it, so a change made to it later is still seen by ``save``. A record that
    differs from the database is never let go before it is saved.

    Looking up an id costs one query the first time. Iterating the table reads
    all of it and is logged: callers that want a subset ask the repository's
    ``find`` instead.
    """

    def __init__(
        self,
        kind: str,
        *,
        load_one: Callable[[str], Any | None],
        load_all: Callable[[], Iterable[tuple[str, Any]]],
        fingerprint: Callable[[Any], bytes],
        max_cached: int | None = 500,
    ) -> None:
        self.kind = kind
        self._load_one = load_one
        self._load_all = load_all
        self._fingerprint = fingerprint
        self._max_cached = max_cached
        self._recent: OrderedDict[str, Any] = OrderedDict()
        # Only used when records can be let go; plain dict values cannot be
        # weakly referenced, and a table of those is kept whole.
        self._alive: weakref.WeakValueDictionary[str, Any] | None = (
            weakref.WeakValueDictionary() if max_cached is not None else None
        )
        self._stored: dict[str, bytes] = {}
        self._lock = threading.RLock()
        self.full_reads = 0

    # -- lookups -----------------------------------------------------------

    def _cached(self, key: str) -> Any | None:
        value = self._recent.get(key)
        if value is not None:
            self._recent.move_to_end(key)
            return value
        if self._alive is not None:
            value = self._alive.get(key)
            if value is not None:
                self._recent[key] = value
                self._trim()
        return value

    def _lookup(self, key: Any) -> Any | None:
        if not isinstance(key, str):
            return None
        with self._lock:
            value = self._cached(key)
            if value is not None:
                return value
            value = self._load_one(key)
            if value is None:
                return None
            return self._admit(key, value)

    def __getitem__(self, key: str) -> Any:
        value = self._lookup(key)
        if value is None:
            raise KeyError(key)
        return value

    def __contains__(self, key: object) -> bool:
        return self._lookup(key) is not None

    # -- changes -----------------------------------------------------------

    def __setitem__(self, key: str, value: Any) -> None:
        with self._lock:
            self._recent[key] = value
            self._recent.move_to_end(key)
            if self._alive is not None:
                self._alive[key] = value
            self._trim()

    def __delitem__(self, key: str) -> None:
        """Forget a record. Removing its row is the repository's job."""
        with self._lock:
            known = self._recent.pop(key, None) is not None
            if self._alive is not None and self._alive.pop(key, None) is not None:
                known = True
            self._stored.pop(key, None)
            if not known and self._load_one(key) is None:
                raise KeyError(key)

    # -- reading everything --------------------------------------------------

    def _everything(self) -> dict[str, Any]:
        with self._lock:
            self.full_reads += 1
            logger.warning("full_table_read", extra={"path": self.kind})
            records = {key: self._admit(key, value) for key, value in self._load_all()}
            # Records made here and not saved yet are part of the table too.
            for key, value in self.loaded():
                records.setdefault(key, value)
            return records

    def __iter__(self) -> Iterator[str]:
        return iter(self._everything())

    def __len__(self) -> int:
        return len(self._everything())

    def values(self):  # type: ignore[override]
        return self._everything().values()

    def items(self):  # type: ignore[override]
        return self._everything().items()

    # -- for the repository --------------------------------------------------

    def _admit(self, key: str, value: Any) -> Any:
        """Take a record just read from the database, unless it is already held."""
        existing = self._cached(key)
        if existing is not None:
            return existing
        self._recent[key] = value
        if self._alive is not None:
            self._alive[key] = value
        self._stored[key] = self._fingerprint(value)
        self._trim()
        return value

    def admit(self, rows: Iterable[tuple[str, Any]]) -> list[Any]:
        """Records just read from the database, as the objects this table hands out."""
        with self._lock:
            return [self._admit(key, value) for key, value in rows]

    def loaded(self) -> list[tuple[str, Any]]:
        """Every record currently held, whether or not it has been saved."""
        with self._lock:
            records = dict(self._alive.items()) if self._alive is not None else {}
            records.update(self._recent)
            return list(records.items())

    def changed(self) -> list[tuple[str, Any, bytes]]:
        """Held records that differ from what the database last had, with their new fingerprint."""
        changed = []
        for key, value in self.loaded():
            fingerprint = self._fingerprint(value)
            if self._stored.get(key) != fingerprint:
                changed.append((key, value, fingerprint))
        return changed

    def mark_stored(self, key: str, fingerprint: bytes) -> None:
        with self._lock:
            self._stored[key] = fingerprint

    def forget_unheld(self) -> None:
        """Drop the bookkeeping of records nobody holds any more."""
        if self._alive is None:
            return
        with self._lock:
            for key in [key for key in self._stored if key not in self._recent and key not in self._alive]:
                del self._stored[key]

    def _trim(self) -> None:
        if self._max_cached is None:
            return
        excess = len(self._recent) - self._max_cached
        if excess <= 0:
            return
        # Oldest first. A record that has not been saved stays where it is.
        for key in list(self._recent)[: excess + 16]:
            if excess <= 0:
                break
            value = self._recent[key]
            if self._stored.get(key) == self._fingerprint(value):
                del self._recent[key]
                excess -= 1
