"""Inspect font subsets and text codes in Kehot cover PDFs."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ContentStream


def raw_hex(value):
    if isinstance(value, (int, float)):
        return value
    return value.original_bytes.hex()


def font_stream(font):
    font = font.get_object()
    if font.get("/DescendantFonts"):
        descriptor = font["/DescendantFonts"][0].get_object().get("/FontDescriptor")
    else:
        descriptor = font.get("/FontDescriptor")
    if not descriptor:
        return None
    descriptor = descriptor.get_object()
    for key in ("/FontFile2", "/FontFile3", "/FontFile"):
        if descriptor.get(key):
            return descriptor[key].get_object().get_data()
    return None


def inspect(pdf_path: Path, extract_root: Path | None, all_pages: bool) -> None:
    reader = PdfReader(pdf_path)
    page = reader.pages[0]
    print(f"\n## {pdf_path.name} | {list(page.mediabox)} | {len(reader.pages)} pages")
    pages = reader.pages if all_pages else reader.pages[:1]
    seen_fonts = set()
    for page_index, page in enumerate(pages, start=1):
        fonts = page.get("/Resources", {}).get("/Font", {})
        print(f"PAGE {page_index}")
        for resource_name, reference in fonts.items():
            font = reference.get_object()
            data = font_stream(reference)
            digest = hashlib.sha256(data).hexdigest()[:16] if data else "-"
            font_key = (str(resource_name), str(font.get("/BaseFont")), digest)
            if font_key not in seen_fonts:
                seen_fonts.add(font_key)
                print(
                    "FONT",
                    resource_name,
                    font.get("/BaseFont"),
                    font.get("/Subtype"),
                    f"bytes={len(data) if data else 0}",
                    f"sha256={digest}",
                )
                if data and extract_root:
                    target = extract_root / pdf_path.stem / f"{str(resource_name)[1:]}-{str(font.get('/BaseFont')).split('+')[-1][1:]}.ttf"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)

        content = ContentStream(page.get_contents(), reader)
        current_font = ""
        text_matrix = None
        for operands, operator in content.operations:
            if operator == b"Tf":
                current_font = str(operands[0])
            elif operator == b"Tm":
                text_matrix = tuple(float(value) for value in operands)
            elif operator == b"Tj":
                print("TEXT", current_font, text_matrix, "Tj", raw_hex(operands[0]))
            elif operator == b"TJ":
                print("TEXT", current_font, text_matrix, "TJ", [raw_hex(item) for item in operands[0]])


parser = argparse.ArgumentParser()
parser.add_argument("pdfs", nargs="+", type=Path)
parser.add_argument("--extract-root", type=Path)
parser.add_argument("--all-pages", action="store_true")
arguments = parser.parse_args()

for pdf in arguments.pdfs:
    inspect(pdf, arguments.extract_root, arguments.all_pages)
