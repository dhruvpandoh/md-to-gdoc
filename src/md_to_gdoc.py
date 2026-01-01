"""Markdown Meeting Notes, Google Doc (Google Docs API)

This module is designed to be used from Google Colab.
It parses a constrained markdown format (headings, bullets, checkboxes, hr, footer)
and creates a formatted Google Doc.

Usage (Colab):
    from google.colab import auth
    auth.authenticate_user()

    from md_to_gdoc import parse_markdown, create_formatted_doc
    paragraphs = parse_markdown(MARKDOWN_NOTES)
    url = create_formatted_doc(paragraphs, doc_title="Product Team Sync")
    print(url)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

DOCS_SCOPES = ["https://www.googleapis.com/auth/documents"]
MENTION_RE = re.compile(r"@\w+")


@dataclass
class Paragraph:
    kind: str  
    text: str
    level: int = 0  
    mentions: Tuple[Tuple[int, int], ...] = ()


def _mention_spans(s: str) -> Tuple[Tuple[int, int], ...]:
    return tuple((m.start(), m.end()) for m in MENTION_RE.finditer(s))


def parse_markdown(md: str) -> List[Paragraph]:
    """Parse markdown meeting notes into paragraph objects."""
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: List[Paragraph] = []
    in_footer = False

    for raw in lines:
        line = raw.rstrip()

        if not line.strip():
            out.append(Paragraph(kind="text", text=""))
            continue

        if line.strip() == "---":
            out.append(Paragraph(kind="hr", text=""))
            in_footer = True
            continue

        if line.startswith("# "):
            title = line[2:].strip()
            main, _, rest = title.partition(" - ")
            out.append(Paragraph(kind="h1", text=main.strip()))
            if rest.strip():
                out.append(Paragraph(kind="text", text=rest.strip()))
            continue

        if line.startswith("## "):
            out.append(Paragraph(kind="h2", text=line[3:].strip()))
            continue

        if line.startswith("### "):
            out.append(Paragraph(kind="h3", text=line[4:].strip()))
            continue

        m_cb = re.match(r"^(\s*)-\s*\[ \]\s+(.*)$", line)
        if m_cb:
            level = len(m_cb.group(1)) // 2
            txt = m_cb.group(2).strip()
            out.append(Paragraph(kind="checkbox", text=txt, level=level, mentions=_mention_spans(txt)))
            continue

        m_b = re.match(r"^(\s*)([-*])\s+(.*)$", line)
        if m_b:
            level = len(m_b.group(1)) // 2
            txt = m_b.group(3).strip()
            kind = "footer" if in_footer else "bullet"
            out.append(Paragraph(kind=kind, text=txt, level=level, mentions=_mention_spans(txt)))
            continue

        txt = line.strip()
        out.append(Paragraph(kind=("footer" if in_footer else "text"), text=txt, mentions=_mention_spans(txt)))

    return out


def create_formatted_doc(paragraphs: List[Paragraph], doc_title: str = "Meeting Notes") -> str:
    """Create and format a Google Doc. Returns the Doc URL."""
    try:
        creds, _ = google.auth.default(scopes=DOCS_SCOPES)
        service = build("docs", "v1", credentials=creds)
    except Exception as e:
        raise RuntimeError(f"Auth/build failed: {e}") from e

    try:
        doc = service.documents().create(body={"title": doc_title}).execute()
        doc_id = doc["documentId"]
    except HttpError as e:
        raise RuntimeError(f"Failed to create doc (is Docs API enabled?): {e}") from e

    idx = 1
    requests: List[Dict[str, Any]] = []
    para_ranges: List[Dict[str, Any]] = []
    mention_ranges: List[Tuple[int, int]] = []
    footer_ranges: List[Tuple[int, int]] = []

    def add_text(text: str) -> Tuple[int, int]:
        nonlocal idx
        requests.append({"insertText": {"location": {"index": idx}, "text": text + "\n"}})
        start = idx
        end = idx + len(text) + 1
        idx = end
        return start, end

    for p in paragraphs:
        if p.kind == "hr":
            add_text("")
            requests.append({"insertHorizontalRule": {"location": {"index": idx}}})
            idx += 1
            add_text("")
            continue

        start, end = add_text(p.text)
        para_ranges.append({"kind": p.kind, "level": p.level, "start": start, "end": end})
        for ms, me in p.mentions:
            mention_ranges.append((start + ms, start + me))
        if p.kind == "footer":
            footer_ranges.append((start, end - 1))

    style_reqs: List[Dict[str, Any]] = []

    def paragraph_named_style(start: int, end: int, style: str) -> None:
        style_reqs.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"namedStyleType": style},
                "fields": "namedStyleType",
            }
        })

    def set_indent(start: int, end: int, level: int) -> None:
        style_reqs.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"indentStart": {"magnitude": 36 * level, "unit": "PT"}},
                "fields": "indentStart",
            }
        })

    for pr in para_ranges:
        if pr["kind"] == "h1":
            paragraph_named_style(pr["start"], pr["end"], "HEADING_1")
        elif pr["kind"] == "h2":
            paragraph_named_style(pr["start"], pr["end"], "HEADING_2")
        elif pr["kind"] == "h3":
            paragraph_named_style(pr["start"], pr["end"], "HEADING_3")

    for pr in para_ranges:
        if pr["kind"] == "bullet":
            set_indent(pr["start"], pr["end"], pr["level"])
            style_reqs.append({
                "createParagraphBullets": {
                    "range": {"startIndex": pr["start"], "endIndex": pr["end"]},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            })
        elif pr["kind"] == "checkbox":
            set_indent(pr["start"], pr["end"], pr["level"])
            style_reqs.append({
                "createParagraphBullets": {
                    "range": {"startIndex": pr["start"], "endIndex": pr["end"]},
                    "bulletPreset": "BULLET_CHECKBOX",
                }
            })

    for s, e in mention_ranges:
        style_reqs.append({
            "updateTextStyle": {
                "range": {"startIndex": s, "endIndex": e},
                "textStyle": {
                    "bold": True,
                    "foregroundColor": {"color": {"rgbColor": {"red": 0.10, "green": 0.35, "blue": 0.85}}},
                },
                "fields": "bold,foregroundColor",
            }
        })

    for s, e in footer_ranges:
        style_reqs.append({
            "updateTextStyle": {
                "range": {"startIndex": s, "endIndex": e},
                "textStyle": {
                    "italic": True,
                    "foregroundColor": {"color": {"rgbColor": {"red": 0.45, "green": 0.45, "blue": 0.45}}},
                    "fontSize": {"magnitude": 9, "unit": "PT"},
                },
                "fields": "italic,foregroundColor,fontSize",
            }
        })

    try:
        service.documents().batchUpdate(documentId=doc_id, body={"requests": requests + style_reqs}).execute()
    except HttpError as e:
        raise RuntimeError(f"Docs batchUpdate failed: {e}") from e

    return f"https://docs.google.com/document/d/{doc_id}/edit"
