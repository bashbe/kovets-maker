"""Build a browser-ready Hatzvi title font from a supplied cover PDF.

The InDesign cover keeps a complete Unicode cmap in one embedded subset and
the actual Hebrew title outlines in another.  Both subsets retain the same
glyph IDs, so the outlines can be merged without tracing or redrawing them.
"""

from __future__ import annotations

import argparse
import copy
import io
from pathlib import Path

from fontTools.ttLib import TTFont
from pypdf import PdfReader


def font_bytes(font_reference) -> bytes:
    font = font_reference.get_object()
    descendant = font.get("/DescendantFonts")
    if descendant:
        descriptor = descendant[0].get_object().get("/FontDescriptor")
    else:
        descriptor = font.get("/FontDescriptor")
    if not descriptor:
        raise RuntimeError("The embedded font has no descriptor.")
    descriptor = descriptor.get_object()
    for key in ("/FontFile2", "/FontFile3", "/FontFile"):
        if descriptor.get(key):
            return descriptor[key].get_object().get_data()
    raise RuntimeError("The embedded font program was not found.")


def has_outline(font: TTFont, glyph_id: int) -> bool:
    glyph_name = font.getGlyphOrder()[glyph_id]
    return font["glyf"][glyph_name].numberOfContours != 0


def build(source: Path, destination: Path) -> None:
    page = PdfReader(source).pages[0]
    fonts = page["/Resources"]["/Font"]
    outline_font = TTFont(io.BytesIO(font_bytes(fonts["/C2_6"])))
    unicode_font = TTFont(io.BytesIO(font_bytes(fonts["/TT1"])))
    glyph_order = unicode_font.getGlyphOrder()

    for glyph_id, glyph_name in enumerate(glyph_order):
        if glyph_id >= len(outline_font.getGlyphOrder()) or not has_outline(outline_font, glyph_id):
            continue
        source_name = outline_font.getGlyphOrder()[glyph_id]
        unicode_font["glyf"][glyph_name] = copy.deepcopy(outline_font["glyf"][source_name])
        unicode_font["hmtx"].metrics[glyph_name] = outline_font["hmtx"].metrics[source_name]

    # Missing subset glyphs must remain unmapped so CSS can fall back to the
    # Narkis face instead of rendering an invisible glyph.
    for cmap in unicode_font["cmap"].tables:
        cmap.cmap = {
            codepoint: glyph_name
            for codepoint, glyph_name in cmap.cmap.items()
            if glyph_name in glyph_order
            and (
                codepoint == 0x20
                or unicode_font["glyf"][glyph_name].numberOfContours != 0
            )
        }

    family = "PDF MHatzvi Rebuilt"
    style = "Bold"
    full_name = f"{family} {style}"
    for platform_id, encoding_id, language_id in ((3, 1, 0x409), (1, 0, 0)):
        unicode_font["name"].setName(family, 1, platform_id, encoding_id, language_id)
        unicode_font["name"].setName(style, 2, platform_id, encoding_id, language_id)
        unicode_font["name"].setName(full_name, 4, platform_id, encoding_id, language_id)
        unicode_font["name"].setName(full_name.replace(" ", "-"), 6, platform_id, encoding_id, language_id)
    unicode_font["OS/2"].usWeightClass = 700
    unicode_font["head"].macStyle = 1
    unicode_font["head"].created = 2082844800
    unicode_font["head"].modified = 2082844800

    destination.parent.mkdir(parents=True, exist_ok=True)
    unicode_font.save(destination, reorderTables=False)
    print(f"Created {destination} from {source}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    build(arguments.source, arguments.destination)


if __name__ == "__main__":
    main()
