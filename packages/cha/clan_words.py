"""Read a CHAT main tier the way CLAN counts it.

The rules follow CLAN's KIDEVAL and MLU commands. They were taken from the
official OSX-CLAN source (V 07-Aug-2026, ``kideval.cpp``, ``mlu.cpp``,
``mllib.cpp``, ``cutt.cpp``) and the strings and calls they rely on were
checked against the CLANc 4.13 binary (V 01-May-2026):

* Retraced material is not counted: ``<...> [/]``, ``[//]``, ``[///]``,
  ``[/-]`` and ``[/?]`` remove the word or group before them (``R6`` is off
  for MLU, FREQ and KIDEVAL).
* Words starting with ``0``, ``&``, ``+``, ``-`` or ``#`` are not words
  (omissions, fillers, fragments, events, terminators, pauses), nor are timed
  pauses such as ``(.)`` or ``(1.5)``.
* ``(be)cause`` counts as ``because`` (``Parans = 1``), ``goed [: went]``
  counts as ``went`` (``R5`` on), and ``ice+cream`` is one word.
* An utterance with ``[+ exc]`` or ``www`` is left out of every measure.
  One with ``xxx``, ``yyy``, ``www`` or ``[+ mlue]`` is left out of MLU but
  still counts towards FREQ.
* ``[/]`` and ``[//]`` are counted as repetitions and retracings, ``[*]`` as
  word errors (one per word in an ``<...>`` group), and the post-codes
  ``[+ *]``, ``[+ jar]``, ``[+ es]``, ``[+ cir]``, ``[+ per]``, ``[+ gram]``
  as utterance errors.

CLAN expects words to be separated by spaces. Thai is written without them,
so each Thai word is segmented with PyThaiNLP (newmm) after the CHAT codes are
removed. A repetition mark ``ๆ`` stays with the word it repeats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import re

_MEDIA_BULLET = re.compile(r"\x15[^\x15]*\x15")
_TOKEN = re.compile(r"\[[^\]]*\]|\+<|<|>|[^\s<>\[\]]+")
_PAUSE = re.compile(r"\(\s*[\d.:]*\s*\)")
_THAI = re.compile(r"[฀-๿]")
_THAI_REPEAT = "ๆ"

RETRACE_CODES = {"/", "//", "///", "/-", "/?"}
UNINTELLIGIBLE = {"xxx", "yyy", "www"}
UTTERANCE_ERROR_POSTCODES = {"*", "jar", "es", "cir", "per", "gram"}
# Utterance terminators after which a "+," line continues the same utterance.
CONTINUATION_TERMINATORS = {"+/.", "+//.", "+/?", "+//?", "+...", "+..?"}
_NOT_WORD_START = ("0", "&", "+", "-", "#")
# CHAT punctuation, intonation and CA marks that are not part of a word.
_STRIP_CHARS = ",;.?!„‡“”\"↑↓≈≋∆∇°▁▔☺♋⁇∬Ϋ∲§∾↻⇗↗→↘⇘∙ˈˌ:^"


@dataclass(frozen=True)
class MainTierAnalysis:
    """What CLAN would count on one main tier line."""

    words: tuple[str, ...]
    """Countable words, lower-cased, with replacements applied."""
    spoken_words: tuple[str, ...]
    """Every spoken word, retraced material included; for repetition cues."""
    unintelligible_count: int = 0
    has_www: bool = False
    has_unintelligible: bool = False
    postcodes: tuple[str, ...] = ()
    repetitions: int = 0
    retracings: int = 0
    word_errors: int = 0
    utterance_errors: int = 0
    self_completion: bool = False
    """Starts with ``+,``: continues the speaker's interrupted utterance."""
    continues: bool = False
    """Ends with a terminator that a later ``+,`` line may continue."""

    @property
    def excluded(self) -> bool:
        """Left out of every measure (``[+ exc]`` or ``www``)."""
        return self.has_www or "exc" in self.postcodes

    @property
    def mlu_excluded(self) -> bool:
        """Left out of MLU (also ``xxx``/``yyy`` or ``[+ mlue]``)."""
        return self.excluded or self.has_unintelligible or "mlue" in self.postcodes


@dataclass
class _Word:
    text: str
    groups: tuple[int, ...]
    retraced: bool = False
    replacement: list[str] | None = None


@dataclass
class _Scan:
    words: list[_Word] = field(default_factory=list)
    postcodes: list[str] = field(default_factory=list)
    repetitions: int = 0
    retracings: int = 0
    word_errors: int = 0
    terminators: list[str] = field(default_factory=list)


def analyze_main_tier(text: str) -> MainTierAnalysis:
    """Apply CLAN's word and utterance rules to one main tier line."""
    scan = _scan(_MEDIA_BULLET.sub(" ", str(text or "")))
    words: list[str] = []
    spoken: list[str] = []
    unintelligible = 0
    has_www = False
    for word in scan.words:
        for kind, value in _word_forms(word.text):
            if kind == "word":
                spoken.append(value)
        if word.retraced:
            continue
        sources = word.replacement if word.replacement is not None else [word.text]
        for source in sources:
            for kind, value in _word_forms(source):
                if kind == "word":
                    words.append(value)
                elif kind == "unintelligible":
                    unintelligible += 1
                    has_www = has_www or value == "www"
    # KIDEVAL drops a www utterance even when the www is retraced.
    has_www = has_www or any(_base(word.text) == "www" for word in scan.words)
    postcodes = tuple(scan.postcodes)
    return MainTierAnalysis(
        words=tuple(words),
        spoken_words=tuple(spoken),
        unintelligible_count=unintelligible,
        has_www=has_www,
        has_unintelligible=unintelligible > 0,
        postcodes=postcodes,
        repetitions=scan.repetitions,
        retracings=scan.retracings,
        word_errors=scan.word_errors,
        utterance_errors=sum(1 for code in postcodes if code in UTTERANCE_ERROR_POSTCODES),
        self_completion="+," in scan.terminators,
        continues=any(term in CONTINUATION_TERMINATORS for term in scan.terminators),
    )


def countable_words(text: str) -> list[str]:
    """The words CLAN counts on one main tier line."""
    return list(analyze_main_tier(text).words)


def mor_stems(mor_text: str) -> list[str]:
    """Lemmas on a ``%mor`` tier, as KIDEVAL's FREQ counts them.

    Clitics (``~``, ``$``) are separate items; a compound
    (``n|+n|ice+n|cream``) is one item made of its stems. Punctuation and
    ``end``/``beg``/``cm``/``bq``/``eq`` items and unintelligible words are
    skipped.
    """
    stems: list[str] = []
    for item in str(mor_text or "").split():
        for part in re.split(r"[~$]", item):
            if "|" not in part:
                continue
            pos, _, rest = part.partition("|")
            if pos.split(":")[0] in {"end", "beg", "cm", "bq", "eq", "bq2", "eq2"}:
                continue
            if rest.startswith("+"):
                stem = "".join(_mor_stem(piece.partition("|")[2]) for piece in rest[1:].split("+") if "|" in piece)
            else:
                stem = _mor_stem(rest)
            stem = stem.lower()
            if not stem or stem[0] in "+-!?." or stem in UNINTELLIGIBLE:
                continue
            stems.append(stem)
    return stems


def _mor_stem(value: str) -> str:
    return re.split(r"[-&=#]", value, maxsplit=1)[0]


def _scan(text: str) -> _Scan:
    scan = _Scan()
    stack: list[int] = []
    next_group = 0
    scope: tuple[str, int] | None = None
    for token in _TOKEN.findall(text):
        if token == "<":
            stack.append(next_group)
            next_group += 1
            scope = None
        elif token == ">":
            if stack:
                scope = ("group", stack.pop())
        elif token.startswith("["):
            _apply_code(scan, token[1:-1].strip(), _scope_words(scan, scope))
        elif token.startswith("+") and not token.startswith("+\""):
            scan.terminators.append(token)
            scope = None
        else:
            scan.words.append(_Word(token, tuple(stack)))
            scope = ("word", len(scan.words) - 1)
    return scan


def _scope_words(scan: _Scan, scope: tuple[str, int] | None) -> list[_Word]:
    if scope is None:
        return []
    kind, key = scope
    if kind == "word":
        return [scan.words[key]]
    return [word for word in scan.words if key in word.groups]


def _apply_code(scan: _Scan, code: str, scope: list[_Word]) -> None:
    code = re.sub(r"\s+", " ", code)
    if code in RETRACE_CODES:
        for word in scope:
            word.retraced = True
        if code == "/":
            scan.repetitions += 1
        elif code == "//":
            scan.retracings += 1
    elif code.startswith(":") and scope:
        target = code.lstrip(":").split()
        scope[0].replacement = target
        for word in scope[1:]:
            word.replacement = []
    elif code.startswith("*"):
        scan.word_errors += max(1, len(scope))
    elif code.startswith("+"):
        scan.postcodes.append(code[1:].strip().lower())


def _base(token: str) -> str:
    return token.split("@", 1)[0].lower()


def _word_forms(token: str) -> list[tuple[str, str]]:
    """(kind, form) for one transcribed token: a word, xxx/yyy/www, or nothing."""
    if not token or token.startswith(_NOT_WORD_START) or _PAUSE.fullmatch(token):
        return []
    base = _base(token)
    if base.strip(_STRIP_CHARS) in UNINTELLIGIBLE:
        return [("unintelligible", base.strip(_STRIP_CHARS))]
    word = base.replace("(", "").replace(")", "")
    word = word.translate(_STRIP_TABLE).strip()
    if not word or not any(ch.isalnum() for ch in word):
        return []
    if _THAI.search(word):
        return [("word", piece) for piece in _segment_thai(word)]
    return [("word", word)]


_STRIP_TABLE = str.maketrans("", "", _STRIP_CHARS)


@lru_cache(maxsize=8192)
def _segment_thai(text: str) -> tuple[str, ...]:
    try:
        from pythainlp.tokenize import word_tokenize

        pieces = word_tokenize(text, engine="newmm", keep_whitespace=False)
    except Exception:  # noqa: BLE001 - fall back to the unsegmented word
        pieces = [text]
    words: list[str] = []
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if piece == _THAI_REPEAT:
            if words:
                words[-1] += _THAI_REPEAT
            continue
        if any(ch.isalnum() or _THAI.match(ch) for ch in piece):
            words.append(piece)
    return tuple(words)


def chat_code_problems(text: str) -> list[str]:
    """Problems in the CHAT codes of one main tier that would change what CLAN counts.

    Checks what the counting rules rely on: balanced ``[ ]`` and ``< >``,
    a word or ``<...>`` group before each scoped code, a target inside
    ``[: ]``, and no bare ``&`` or ``0``. It is not a full CHAT validator.
    """
    problems: list[str] = []
    line = _MEDIA_BULLET.sub(" ", str(text or ""))
    depth = 0
    for char in line:
        if char == "[":
            depth += 1
            if depth > 1:
                problems.append("วงเล็บ [ ] ซ้อนกัน")
                break
        elif char == "]":
            depth -= 1
            if depth < 0:
                problems.append("มี ] โดยไม่มี [ เปิด")
                break
    if depth > 0:
        problems.append("มี [ ที่ไม่ได้ปิดด้วย ]")
    tokens = _TOKEN.findall(line)
    if tokens.count("<") != tokens.count(">"):  # "+<" is its own token, not a group
        problems.append("< > ไม่ครบคู่")
    previous: str | None = None
    for token in tokens:
        if token.startswith("["):
            code = re.sub(r"\s+", " ", token[1:-1].strip())
            scoped = code in RETRACE_CODES or code.startswith((":", "*", "=", "!", "?", "%"))
            if scoped and previous not in ("word", ">"):
                problems.append(f"[{code}] ต้องตามหลังคำหรือกลุ่ม <...>")
            if code.startswith(":") and not code.lstrip(":").strip():
                problems.append("[: ] ยังไม่ได้ใส่คำที่ตั้งใจพูด")
            continue
        if token in ("<", "+<"):
            previous = "<"
        elif token == ">":
            previous = ">"
        elif token.startswith("+"):
            previous = None
        else:
            if token in ("&", "&-", "&+", "&=", "0"):
                problems.append(f"รหัส {token} ไม่มีคำตามหลัง")
            previous = "word"
    return list(dict.fromkeys(problems))
