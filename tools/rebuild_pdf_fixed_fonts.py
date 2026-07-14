"""Rebuild Unicode cmaps for the subset fonts used by fixed cover text.

The first PDF page embeds Identity-H TrueType subsets without ToUnicode maps.
Its character codes are glyph IDs, so the mappings below are reconstructed from
the known, non-editable text printed on that page.
"""

from pathlib import Path

from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable


SOURCE = Path("tmp/pdfs/fonts")
TARGET = Path("assets/fonts")


def cids(hex_string: str) -> list[int]:
    raw = bytes.fromhex(hex_string)
    return [int.from_bytes(raw[index : index + 2], "big") for index in range(0, len(raw), 2)]


def reversed_pair(hex_string: str, logical_text: str) -> tuple[list[int], str]:
    return cids(hex_string), logical_text[::-1]


FONT_SPECS = {
    "PDF JBilna Bold": {
        "source": "TT1-JBilna-Bold.ttf",
        "target": "PDF-JBilna-Bold.ttf",
        "pairs": [
            reversed_pair("00c900b800b900b500b500b000b100b500b900bc", "ליובאוויטש"),
            reversed_pair("00bd00b900b300b900c100b700b400f300c800c600b500b0", "אוצר החסידים"),
            ([0x97], "—"),
            reversed_pair("00b900c800c400c1", "ספרי"),
            reversed_pair("00ca00c900b500b300c700f300b300b500b100bb", "כבוד קדושת"),
            reversed_pair("00c200b900b600f300be00b200b100c000f300b400b400bc00bc00c700b500c600b6", "זצוקללהה נבגמ זיע"),
        ],
    },
    "PDF JName": {
        "source": "TT2-JName.ttf",
        "target": "PDF-JName.ttf",
        "pairs": [
            ([0x92], "׳"),
            reversed_pair("00c000b700c400c600c2008c00c100bb00c400c2008c00cc008e00b900c200b700b4", "אדמו״ר מנחם מענדל"),
            ([0x8E], "״"),
        ],
    },
    "PDF JNarkis Bold": {
        "source": "TT3-JNarkis-Bold.ttf",
        "target": "PDF-JNarkis-Bold.ttf",
        "pairs": [
            reversed_pair("00bd00b200ae00bf00c600b300ae00b700be00c7", "שניאורסאהן"),
        ],
    },
    "PDF JNarkis": {
        "source": "TT4-JNarkis.ttf",
        "target": "PDF-JNarkis.ttf",
        "pairs": [
            reversed_pair("00ad009c009d00990099009400950099009d00a000a2", "מליובאוויטש"),
            reversed_pair("00ae009f00ac00a600a20003009d0097009d000300a000a6000300ac0099009400a00003009400aa0099009d", "יוצא לאור על ידי מערכת"),
            reversed_pair("00980094009d00ac009500a0000300ad00ad0099000300a1009d00a4009900a200ad000300ae0099009400a2000300a6009500ad000300a1009d00a800a00094000300ae00ad00a2009b000300ae00a400ad", "שנת חמשת אלפים שבע מאות שמונים ושש לבריאה"),
        ],
    },
}


def build_mapping(pairs: list[tuple[list[int], str]]) -> dict[int, int]:
    glyph_to_unicode: dict[int, int] = {}
    for glyph_ids, visual_text in pairs:
        if len(glyph_ids) != len(visual_text):
            raise ValueError(f"Length mismatch: {len(glyph_ids)} glyphs for {visual_text!r} ({len(visual_text)} chars)")
        for glyph_id, character in zip(glyph_ids, visual_text):
            unicode_value = ord(character)
            previous = glyph_to_unicode.get(glyph_id)
            if previous is not None and previous != unicode_value:
                raise ValueError(f"Glyph {glyph_id} maps to both U+{previous:04X} and U+{unicode_value:04X}")
            glyph_to_unicode[glyph_id] = unicode_value
    return glyph_to_unicode


def rebuild_font(family: str, spec: dict) -> None:
    font = TTFont(SOURCE / spec["source"])
    glyph_order = font.getGlyphOrder()
    glyph_to_unicode = build_mapping(spec["pairs"])
    unicode_to_glyph = {unicode_value: glyph_order[glyph_id] for glyph_id, unicode_value in glyph_to_unicode.items()}

    cmap = CmapSubtable.newSubtable(4)
    cmap.platformID = 3
    cmap.platEncID = 1
    cmap.language = 0
    cmap.cmap = unicode_to_glyph
    if "cmap" not in font:
        font["cmap"] = newTable("cmap")
        font["cmap"].tableVersion = 0
    font["cmap"].tables = [cmap]

    # Remove the PDF subset prefix from human-readable names for easier inspection.
    for name_id, value in ((1, family), (4, family), (6, family.replace(" ", "-"))):
        font["name"].setName(value, name_id, 3, 1, 0x409)
        font["name"].setName(value, name_id, 1, 0, 0)

    TARGET.mkdir(parents=True, exist_ok=True)
    output = TARGET / spec["target"]
    font.save(output)
    print(f"{output}: {len(unicode_to_glyph)} Unicode mappings")


for font_family, font_spec in FONT_SPECS.items():
    rebuild_font(font_family, font_spec)
