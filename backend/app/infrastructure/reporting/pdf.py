"""Render a Markdown report to PDF bytes.

Uses reportlab (pure Python) imported lazily so the rest of the app does not
depend on it at import time. Supports the subset of Markdown the report builder
emits: ATX headings (#..###), bullet lists (- ), bold (**...**), inline code,
and paragraphs.
"""
from __future__ import annotations

import html
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_CODE = re.compile(r"`([^`]+?)`")


def _inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = _BOLD.sub(r"<b>\1</b>", escaped)
    escaped = _CODE.sub(r'<font face="Courier">\1</font>', escaped)
    return escaped


def markdown_to_pdf(markdown: str) -> bytes:
    from io import BytesIO

    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], alignment=TA_LEFT, spaceAfter=6)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceBefore=4, spaceAfter=10)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6)
    h3 = ParagraphStyle("h3", parent=styles["Heading3"], spaceBefore=8, spaceAfter=4)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )

    flow: list = []
    bullets: list = []

    def flush_bullets() -> None:
        nonlocal bullets
        if bullets:
            flow.append(
                ListFlowable(
                    [ListItem(Paragraph(b, body)) for b in bullets],
                    bulletType="bullet",
                    leftIndent=12,
                )
            )
            bullets = []

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_bullets()
            flow.append(Spacer(1, 4))
            continue
        if line.startswith("### "):
            flush_bullets()
            flow.append(Paragraph(_inline(line[4:]), h3))
        elif line.startswith("## "):
            flush_bullets()
            flow.append(Paragraph(_inline(line[3:]), h2))
        elif line.startswith("# "):
            flush_bullets()
            flow.append(Paragraph(_inline(line[2:]), h1))
        elif line.startswith("- "):
            bullets.append(_inline(line[2:]))
        else:
            flush_bullets()
            flow.append(Paragraph(_inline(line), body))

    flush_bullets()
    doc.build(flow)
    return buffer.getvalue()
