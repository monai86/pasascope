"""A report as a stand-alone HTML page that reads well in Thai."""

from __future__ import annotations

import html

import markdown2

PAGE = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{
    font-family: "Sarabun", "Thonburi", "Leelawadee UI", "Noto Sans Thai", "Tahoma", sans-serif;
    color: #14213d; background: #ffffff; line-height: 1.7; font-size: 15px;
    max-width: 780px; margin: 32px auto; padding: 0 20px;
  }}
  h1 {{ font-size: 24px; border-bottom: 2px solid #1f5fbf; padding-bottom: 8px; }}
  h2 {{ font-size: 18px; color: #174a96; margin-top: 28px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8px 0; }}
  th, td {{ border: 1px solid #dde3ee; padding: 6px 10px; text-align: left; }}
  td:last-child, th:last-child {{ text-align: right; font-variant-numeric: tabular-nums; }}
  th {{ background: #f4f6fa; }}
  @media print {{ body {{ margin: 0; max-width: none; }} }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def report_html(markdown: str, title: str) -> str:
    body = markdown2.markdown(markdown, extras=["tables", "cuddled-lists"], safe_mode="escape")
    return PAGE.format(title=html.escape(title), body=body)
