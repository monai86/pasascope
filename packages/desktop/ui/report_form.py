"""The parts of a session report the therapist writes, read from and written into its markdown.

The report page offers these as form fields; each field is one section of the
report, so the markdown stays the single record of the report and the PDF
preview shows every keystroke. The measures, cues and limitations stay as the
template drafted them.
"""

from __future__ import annotations

from dataclasses import dataclass

from packages.desktop.core.i18n import report_language


@dataclass(frozen=True)
class Field:
    key: str
    headings: dict[str, str]  # report language → section heading
    kind: str  # "text" (paragraphs as typed) or "list" (one item per line)
    placeholders: tuple[str, ...] = ()  # template lines that mean "not written yet"
    empty: dict[str, str] | None = None  # what an emptied field writes back, per language
    insert_before: tuple[str, ...] = ()  # where a missing section goes


INTERPRETATION = Field(
    "interpretation",
    {"th": "การแปลผลของนักบำบัด", "en": "Therapist's interpretation"},
    "text",
    placeholders=(
        "- (นักบำบัดเขียนการแปลผลและข้อสังเกตจากการบำบัดที่นี่ ก่อนลงนาม)",
        "- (Write your interpretation and clinical observations here before signing.)",
    ),
    empty={
        "th": "- (นักบำบัดเขียนการแปลผลและข้อสังเกตจากการบำบัดที่นี่ ก่อนลงนาม)",
        "en": "- (Write your interpretation and clinical observations here before signing.)",
    },
)
GOALS = Field(
    "goals",
    {"th": "เป้าหมายการบำบัด", "en": "Therapy goals"},
    "list",
    placeholders=("- ยังไม่ได้บันทึกเป้าหมายการบำบัดของเคสนี้", "- No therapy goals are recorded for this case."),
    empty={"th": "- ยังไม่ได้บันทึกเป้าหมายการบำบัดของเคสนี้", "en": "- No therapy goals are recorded for this case."},
)
RECOMMENDATIONS = Field(
    "recommendations",
    {"th": "ข้อเสนอแนะ", "en": "Recommendations"},
    "list",
    insert_before=("ข้อจำกัด", "Limitations", "การลงนามของนักบำบัด", "Therapist sign-off"),
)
FIELDS = (INTERPRETATION, GOALS, RECOMMENDATIONS)


def _span(lines: list[str], heading: str) -> tuple[int, int] | None:
    """(index of "## heading", index of the next "## " heading or the end)."""
    marker = f"## {heading}"
    for start, line in enumerate(lines):
        if line.strip() == marker:
            end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
            return start, end
    return None


def read_field(markdown: str, field: Field) -> str:
    """The field's text as the therapist would type it (no list dashes, no template placeholder)."""
    lines = markdown.splitlines()
    span = _span(lines, field.headings[report_language(markdown)])
    if span is None:
        return ""
    body = [line for line in lines[span[0] + 1:span[1]] if line.strip() not in field.placeholders]
    if field.kind == "list":
        body = [line.strip()[2:] if line.strip().startswith(("- ", "* ")) else line.strip() for line in body]
    return "\n".join(body).strip()


def write_field(markdown: str, field: Field, value: str) -> str:
    """The markdown with the field's section set to ``value``.

    An emptied field gets the template's placeholder back; an empty optional
    section (no placeholder) is removed. A missing section is added before
    the first of ``insert_before`` found, or at the end.
    """
    language = report_language(markdown)
    heading = field.headings[language]
    text = value.strip()
    if field.kind == "list":
        body = [line.strip() if line.strip().startswith(("- ", "* ")) else f"- {line.strip()}"
                for line in text.splitlines() if line.strip()]
    else:
        body = text.splitlines()
    if not body and field.empty:
        body = [field.empty[language]]

    lines = markdown.splitlines()
    span = _span(lines, heading)
    if span is not None:
        start, end = span
        if not body:
            new = lines[:start] + lines[end:]
        else:
            new = lines[:start + 1] + body + [""] + lines[end:]
    elif not body:
        return markdown
    else:
        section = [f"## {heading}", *body, ""]
        at = next((s[0] for s in (_span(lines, h) for h in field.insert_before) if s is not None), len(lines))
        new = lines[:at] + section + lines[at:]
    # One blank line between sections, none doubled.
    out: list[str] = []
    for line in new:
        if line == "" and out and out[-1] == "":
            continue
        out.append(line)
    result = "\n".join(out).rstrip("\n")
    return result + ("\n" if markdown.endswith("\n") else "")
