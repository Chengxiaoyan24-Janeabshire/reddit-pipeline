#!/usr/bin/env python3
"""Rebuild searchable Reddit policy PDFs from the Markdown resources."""
import os
import re
import tempfile
from pathlib import Path

import fitz
import resource_paths

GUIDANCE_ROOT = resource_paths.GUIDANCE_ROOT
PDF_ROOT = resource_paths.RESOURCE_PDF_ROOT
FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]
PAGE_WIDTH, PAGE_HEIGHT = fitz.paper_size("a4")
MARGIN_X = 54
MARGIN_TOP = 56
MARGIN_BOTTOM = 48
FONT_NAME = "ReferenceSans"

FULL_REBUILDS = {
    "Reddit 运营要求.md": "Reddit 运营要求.pdf",
    "Reddit 内容问答.md": "Reddit 内容问答.pdf",
    "Reddit 内容建议及范例.md": "Reddit 内容建议及范例.pdf",
}


def font_path():
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise RuntimeError("No supported CJK font found.")


def clean_inline(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text.strip()


def markdown_blocks(markdown):
    blocks = []
    paragraph = []

    def flush_paragraph():
        if paragraph:
            blocks.append(("paragraph", clean_inline(" ".join(paragraph))))
            paragraph.clear()

    for raw in markdown.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            blocks.append(("space", ""))
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", stripped)
        if heading:
            flush_paragraph()
            blocks.append((f"h{len(heading.group(1))}", clean_inline(heading.group(2))))
            continue
        bullet = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet:
            flush_paragraph()
            blocks.append(("bullet", clean_inline(bullet.group(1))))
            continue
        numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if numbered:
            flush_paragraph()
            blocks.append(("numbered", f"{numbered.group(1)}. {clean_inline(numbered.group(2))}"))
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_paragraph()
            if re.fullmatch(r"[|:\-\s]+", stripped):
                continue
            cells = [clean_inline(cell) for cell in stripped.strip("|").split("|")]
            blocks.append(("table", "  ·  ".join(cells)))
            continue
        paragraph.append(stripped)
    flush_paragraph()
    return blocks


def split_long_token(token, font, size, max_width):
    pieces = []
    current = ""
    for char in token:
        candidate = current + char
        if current and font.text_length(candidate, fontsize=size) > max_width:
            pieces.append(current)
            current = char
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def wrap_text(text, font, size, max_width):
    tokens = re.findall(r"\s+|[\u3400-\u9fff]|[^\s\u3400-\u9fff]+", text)
    lines = []
    current = ""
    for token in tokens:
        if not current and token.isspace():
            continue
        candidate = current + token
        if font.text_length(candidate, fontsize=size) <= max_width:
            current = candidate
            continue
        if current.strip():
            lines.append(current.rstrip())
            current = ""
        token = token.lstrip()
        if not token:
            continue
        if font.text_length(token, fontsize=size) <= max_width:
            current = token
            continue
        pieces = split_long_token(token, font, size, max_width)
        lines.extend(pieces[:-1])
        current = pieces[-1]
    if current.strip():
        lines.append(current.rstrip())
    return lines or [""]


def render_markdown(markdown, font_file):
    doc = fitz.open()
    font = fitz.Font(fontfile=str(font_file))
    page = None
    y = MARGIN_TOP
    page_number = 0

    def new_page():
        nonlocal page, y, page_number
        page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        page.insert_font(fontname=FONT_NAME, fontfile=str(font_file))
        page_number += 1
        y = MARGIN_TOP

    def ensure_space(height):
        nonlocal page
        if page is None or y + height > PAGE_HEIGHT - MARGIN_BOTTOM:
            new_page()

    for kind, text in markdown_blocks(markdown):
        if kind == "space":
            y += 6
            continue
        style = {
            "h1": (20, 29, 12, (0.08, 0.18, 0.32)),
            "h2": (15, 23, 9, (0.10, 0.28, 0.45)),
            "h3": (12.5, 19, 6, (0.12, 0.34, 0.50)),
            "paragraph": (10.5, 16, 5, (0.10, 0.10, 0.10)),
            "bullet": (10.5, 16, 4, (0.10, 0.10, 0.10)),
            "numbered": (10.5, 16, 4, (0.10, 0.10, 0.10)),
            "table": (9.5, 15, 3, (0.16, 0.16, 0.16)),
        }[kind]
        size, line_height, after, color = style
        prefix = "• " if kind == "bullet" else ""
        indent = 16 if kind in {"bullet", "numbered"} else 0
        lines = wrap_text(prefix + text, font, size, PAGE_WIDTH - 2 * MARGIN_X - indent)
        ensure_space(len(lines) * line_height + after)
        for line in lines:
            if y + line_height > PAGE_HEIGHT - MARGIN_BOTTOM:
                new_page()
            page.insert_text(
                (MARGIN_X + indent, y),
                line,
                fontname=FONT_NAME,
                fontsize=size,
                color=color,
            )
            y += line_height
        y += after

    for index, output_page in enumerate(doc):
        output_page.insert_font(fontname=FONT_NAME, fontfile=str(font_file))
        footer = f"{index + 1} / {len(doc)}"
        output_page.insert_text(
            (PAGE_WIDTH - MARGIN_X - 34, PAGE_HEIGHT - 24),
            footer,
            fontname=FONT_NAME,
            fontsize=8,
            color=(0.45, 0.45, 0.45),
        )
    return doc


def save_atomic(doc, output_path):
    fd, temp_name = tempfile.mkstemp(prefix=output_path.stem + "-", suffix=".pdf", dir=output_path.parent)
    os.close(fd)
    try:
        doc.subset_fonts()
        doc.save(temp_name, garbage=4, deflate=True)
        os.replace(temp_name, output_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def rebuild_full(markdown_path, output_path, font_file):
    doc = render_markdown(markdown_path.read_text(), font_file)
    try:
        save_atomic(doc, output_path)
    finally:
        doc.close()


def rebuild_catalog(markdown_path, output_path, font_file):
    existing = fitz.open(output_path)
    if len(existing) < 16:
        existing.close()
        raise RuntimeError(f"{output_path.name} must contain at least 16 catalog pages")
    appendix = render_markdown(markdown_path.read_text(), font_file)
    rebuilt = fitz.open()
    try:
        rebuilt.insert_pdf(existing, from_page=0, to_page=15)
        rebuilt.insert_pdf(appendix)
        save_atomic(rebuilt, output_path)
    finally:
        rebuilt.close()
        appendix.close()
        existing.close()


def main():
    PDF_ROOT.mkdir(parents=True, exist_ok=True)
    selected_font = font_path()
    for markdown_name, pdf_name in FULL_REBUILDS.items():
        rebuild_full(GUIDANCE_ROOT / markdown_name, PDF_ROOT / pdf_name, selected_font)
    rebuild_catalog(
        GUIDANCE_ROOT / "Milvus blog for repurpose.md",
        PDF_ROOT / "Milvus blog for repurpose.pdf",
        selected_font,
    )
    print("Rebuilt 4 Reddit guidance PDFs under resource/reddit/pdfs/.")


if __name__ == "__main__":
    main()
