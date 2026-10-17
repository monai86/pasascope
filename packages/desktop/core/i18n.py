"""English or Thai for the desktop app.

Every piece of interface text is written in both languages where it is used,
``tr("ภาษาไทย", "English")``, so a missing translation cannot slip through.
The language is chosen once, from the workspace profile, before the window
is built (``packages/desktop/app.py``); switching takes effect on restart.
Clinical reports keep their own language (the Thai report template).
"""

from __future__ import annotations

import os
from typing import Any

LANGUAGES = {"en": "English", "th": "ไทย"}
LANGUAGE_ENV = "PASASCOPE_LANGUAGE"
_language = os.environ.get(LANGUAGE_ENV, "en") if os.environ.get(LANGUAGE_ENV) in LANGUAGES else "en"


def set_language(code: str) -> None:
    """Use ``code`` ("en" or "th") from now on; the pipeline's explanations follow it too."""
    global _language
    _language = code if code in LANGUAGES else "en"
    os.environ[LANGUAGE_ENV] = _language


def language() -> str:
    return _language


def tr(thai: str, english: str) -> str:
    """The text in the current language."""
    return english if _language == "en" else thai


class Text:
    """A pair of texts for tables built at import time; read through ``TrDict`` or ``str()``."""

    __slots__ = ("thai", "english")

    def __init__(self, thai: str, english: str) -> None:
        self.thai, self.english = thai, english

    def __str__(self) -> str:
        return tr(self.thai, self.english)

    def __repr__(self) -> str:
        return f"Text({self.thai!r}, {self.english!r})"


def resolve(value: Any) -> Any:
    """Turn every ``Text`` inside ``value`` (also within tuples and lists) into the current language."""
    if isinstance(value, Text):
        return str(value)
    if isinstance(value, tuple):
        return tuple(resolve(item) for item in value)
    if isinstance(value, list):
        return [resolve(item) for item in value]
    return value


class TrDict(dict):
    """A dict whose ``Text`` values come out in the current language."""

    def __getitem__(self, key):
        return resolve(super().__getitem__(key))

    def get(self, key, default=None):
        return resolve(super().get(key, default))

    def items(self):
        return [(key, resolve(value)) for key, value in super().items()]

    def values(self):
        return [resolve(value) for value in super().values()]


class TrList(list):
    """A list whose ``Text`` items come out in the current language."""

    def __getitem__(self, index):
        return resolve(super().__getitem__(index))

    def __iter__(self):
        return (resolve(item) for item in super().__iter__())
