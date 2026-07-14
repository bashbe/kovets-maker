"""Merge the stable PDF font subsets into browser-ready TrueType fonts.

The supplied covers use Identity-H fonts without a ToUnicode table. Their CIDs
are nevertheless stable between documents and map directly to TrueType glyph
IDs. This script unions the non-empty glyph outlines at those IDs, adds a
Unicode cmap, and deliberately leaves unavailable outlines unmapped so that a
CSS fallback font can render them instead of producing an invisible glyph.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable


HEBREW_ALPHABET = "אבגדהוזחטיךכלםמןנסעףפץצקרשת"


SPECS = {
    "narkis-regular": {
        "glob": "*/TT4-Narkis.ttf",
        "family": "PDF JNarkis Rebuilt",
        "style": "Regular",
        "weight": 400,
        "hebrew_start": 0x94,
        "punctuation": {
            0x0020: 0x03,
            0x002C: 0x0D,
            0x002E: 0x0E,
            0x05B7: 0x8A,
            0xFB44: 0xDF,
        },
    },
    "narkis-bold": {
        "glob": "*/TT3-Narkis-Bold.ttf",
        "family": "PDF JNarkis Rebuilt",
        "style": "Bold",
        "weight": 700,
        "hebrew_start": 0xAE,
        "punctuation": {
            0x0020: 0x74,
            0x002C: 0x7F,
            0x002D: 0x80,
            0x05BE: 0x80,
            0x05F3: 0x7A,
            0x05F4: 0x76,
            0x201C: 0x76,
            0x201E: 0xF4,
        },
    },
    "david-regular": {
        "globs": ["*/TT6-David.ttf", "*/TT7-David.ttf"],
        "family": "PDF JDavid Rebuilt",
        "style": "Regular",
        "weight": 400,
        "hebrew_start": 0x96,
        "punctuation": {
            0x0020: 0x03,
            0x002C: 0x0E,
            0x002D: 0xF0,
            0x05BE: 0xF0,
            0x05F3: 0xEB,
            0x05F4: 0x05,
            0x2013: 0xB8,
            0x2014: 0xB8,
        },
    },
    "david-bold": {
        "glob": "*/TT7-David-Bold.ttf",
        "family": "PDF JDavid Rebuilt",
        "style": "Bold",
        "weight": 700,
        "hebrew_start": 0x96,
        "punctuation": {
            0x0020: 0x03,
        },
    },
    "narkis-digits": {
        "glob": "*/TT8-Narkis.ttf",
        "family": "PDF JNarkis Digits",
        "style": "Regular",
        "weight": 400,
        "unicode_to_gid": {
            0x0030: 0x10,
            0x0037: 0x17,
        },
        "coverage_characters": "07",
    },
}


def has_outline(font: TTFont, glyph_id: int) -> bool:
    glyph_name = font.getGlyphOrder()[glyph_id]
    return font["glyf"][glyph_name].numberOfContours != 0


def build_cmap(font: TTFont, unicode_to_gid: dict[int, int]) -> dict[int, str]:
    glyph_order = font.getGlyphOrder()
    cmap = {
        codepoint: glyph_order[glyph_id]
        for codepoint, glyph_id in unicode_to_gid.items()
        if glyph_id < len(glyph_order)
        and (codepoint == 0x20 or has_outline(font, glyph_id))
    }

    cmap_table = newTable("cmap")
    cmap_table.tableVersion = 0
    cmap_table.tables = []
    for platform_id, encoding_id in ((0, 3), (3, 1)):
        subtable = CmapSubtable.newSubtable(4)
        subtable.platformID = platform_id
        subtable.platEncID = encoding_id
        subtable.language = 0
        subtable.cmap = dict(cmap)
        cmap_table.tables.append(subtable)
    font["cmap"] = cmap_table
    return cmap


def rename_font(font: TTFont, family: str, style: str) -> None:
    full_name = f"{family} {style}"
    postscript_name = full_name.replace(" ", "-")
    for platform_id, encoding_id, language_id in ((3, 1, 0x409), (1, 0, 0)):
        font["name"].setName(family, 1, platform_id, encoding_id, language_id)
        font["name"].setName(style, 2, platform_id, encoding_id, language_id)
        font["name"].setName(full_name, 4, platform_id, encoding_id, language_id)
        font["name"].setName(postscript_name, 6, platform_id, encoding_id, language_id)
    font["OS/2"].usWeightClass = 700 if style == "Bold" else 400
    font["head"].macStyle = 1 if style == "Bold" else 0


def ensure_browser_tables(font: TTFont) -> None:
    """Restore the OpenType tables stripped from the PDF subsets.

    Acrobat accepts the compact embedded TrueType programs without a ``post``
    table, but browser font sanitizers reject them.  A format 3 ``post`` table
    is sufficient because the web fonts use the Unicode ``cmap`` added above
    and do not need PostScript glyph names.
    """

    if "post" in font:
        return
    post = newTable("post")
    post.formatType = 3.0
    post.italicAngle = 0
    post.underlinePosition = 0
    post.underlineThickness = 0
    post.isFixedPitch = 0
    post.minMemType42 = 0
    post.maxMemType42 = 0
    post.minMemType1 = 0
    post.maxMemType1 = 0
    font["post"] = post


def unicode_map(spec: dict) -> dict[int, int]:
    if "unicode_to_gid" in spec:
        return dict(spec["unicode_to_gid"])
    mapping = {
        ord(character): spec["hebrew_start"] + index
        for index, character in enumerate(HEBREW_ALPHABET)
    }
    mapping.update(spec["punctuation"])
    return mapping


def merge_font(source_paths: list[Path], spec: dict) -> tuple[TTFont, dict]:
    fonts = [TTFont(path) for path in source_paths]
    glyph_counts = [
        sum(has_outline(font, glyph_id) for glyph_id in range(len(font.getGlyphOrder())))
        for font in fonts
    ]
    base_index = max(range(len(fonts)), key=lambda index: glyph_counts[index])
    merged = fonts[base_index]
    glyph_order = merged.getGlyphOrder()

    for glyph_id, glyph_name in enumerate(glyph_order):
        if has_outline(merged, glyph_id):
            continue
        for source in fonts:
            if glyph_id < len(source.getGlyphOrder()) and has_outline(source, glyph_id):
                merged["glyf"][glyph_name] = copy.deepcopy(source["glyf"][source.getGlyphOrder()[glyph_id]])
                merged["hmtx"].metrics[glyph_name] = source["hmtx"].metrics[source.getGlyphOrder()[glyph_id]]
                break

    mapping = unicode_map(spec)
    cmap = build_cmap(merged, mapping)
    rename_font(merged, spec["family"], spec["style"])
    ensure_browser_tables(merged)
    merged["head"].created = 2082844800
    merged["head"].modified = 2082844800

    coverage_characters = spec.get("coverage_characters", HEBREW_ALPHABET)
    available_characters = [character for character in coverage_characters if ord(character) in cmap]
    missing_characters = [character for character in coverage_characters if ord(character) not in cmap]
    report = {
        "sources": [str(path) for path in source_paths],
        "base_source": str(source_paths[base_index]),
        "source_outline_counts": glyph_counts,
        "merged_outline_count": sum(
            has_outline(merged, glyph_id) for glyph_id in range(len(glyph_order))
        ),
        "available_characters": "".join(available_characters),
        "missing_characters": "".join(missing_characters),
        "mapped_codepoints": len(cmap),
    }
    if coverage_characters == HEBREW_ALPHABET:
        report["available_hebrew"] = report["available_characters"]
        report["missing_hebrew"] = report["missing_characters"]
    return merged, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    report = {}
    for key, spec in SPECS.items():
        patterns = spec.get("globs") or [spec["glob"]]
        source_paths = sorted(
            {path for pattern in patterns for path in args.source_root.glob(pattern)}
        )
        if not source_paths:
            raise SystemExit(f"No source matched {patterns} under {args.source_root}")
        font, font_report = merge_font(source_paths, spec)
        output_path = args.output_dir / f"PDF-{key}.ttf"
        font.save(output_path, reorderTables=False)
        font_report["output"] = str(output_path)
        font_report["output_bytes"] = output_path.stat().st_size
        report[key] = font_report

    report_path = args.output_dir / "pdf-font-coverage.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
