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
import io
import json
from pathlib import Path

from fontTools.cffLib import CFFFontSet
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
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
        "cff_glob": "*/F*-TDavid-Normal.ttf",
        # VTDavid-Normal is the same David drawing family in CFF form.  These
        # are the final Hebrew letters missing from the extracted TrueType
        # subsets; their names come from the PDF's Differences encoding.
        "cff_glyph_map": {
            "Iacute": 0x05DA,  # ך
            "Ocircumflex": 0x05DF,  # ן
            "Ucircumflex": 0x05E3,  # ף
            "dotlessi": 0x05E5,  # ץ
        },
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


def inject_cff_glyphs(font: TTFont, cff_paths: list[Path], spec: dict) -> dict[str, str]:
    """Convert selected raw CFF glyphs into the merged font's ``glyf`` table.

    The PDF CFF sources use a 0.001 FontMatrix while the extracted David
    TrueType files use 2048 units per em.  We therefore scale the outlines by
    2.048 and carry over the PDF advance width and left side bearing.  Cubic
    CFF curves are reduced to quadratic TrueType curves with a sub-unit error.
    """

    glyph_map = spec.get("cff_glyph_map")
    if not glyph_map or not cff_paths:
        return {}

    scale = font["head"].unitsPerEm * 0.001
    glyph_order = font.getGlyphOrder()
    injected: dict[str, str] = {}
    for path in cff_paths:
        cff = CFFFontSet()
        cff.decompile(io.BytesIO(path.read_bytes()), None)
        top = cff[cff.fontNames[0]]
        for cff_name, codepoint in glyph_map.items():
            target_gid = unicode_map(spec)[codepoint]
            if cff_name not in top.CharStrings or target_gid >= len(glyph_order):
                continue
            target_name = glyph_order[target_gid]
            # Prefer the first usable outline; the remaining PDF subsets are
            # duplicates or smaller subsets of the same VTDavid face.
            if target_name in injected:
                continue
            pen = TTGlyphPen(font.getGlyphSet())
            quad_pen = Cu2QuPen(pen, max_err=0.5)
            transform_pen = TransformPen(quad_pen, (scale, 0, 0, scale, 0, 0))
            top.CharStrings[cff_name].draw(transform_pen)
            font["glyf"][target_name] = pen.glyph()

            # PDF Type1 widths are expressed in 1000-unit design space.  The
            # CFF parser exposes the raw PDF width through the font's width
            # array rather than on each charstring, so use the shape bounds for
            # the left side bearing and retain the David default advance when
            # no explicit width is available.
            # ``pen.glyph()`` has already been consumed above; recalculate the
            # left side bearing from the original CFF bounds instead.
            cff_bounds = BoundsPen(None)
            top.CharStrings[cff_name].draw(cff_bounds)
            x_min = round((cff_bounds.bounds[0] if cff_bounds.bounds else 0) * scale)
            # VTDavid's Type1 widths are stable for the injected glyphs.
            width_1000 = {
                "Iacute": 470,
                "Ocircumflex": 304,
                "Ucircumflex": 470,
                "dotlessi": 443,
            }[cff_name]
            font["hmtx"].metrics[target_name] = (round(width_1000 * scale), x_min)
            injected[target_name] = cff_name
    return injected


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

    cff_paths = []
    if spec.get("cff_glob"):
        cff_paths = sorted({path for path in source_paths[0].parent.parent.glob(spec["cff_glob"])})
    injected = inject_cff_glyphs(merged, cff_paths, spec)

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
        "injected_cff_glyphs": injected,
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
