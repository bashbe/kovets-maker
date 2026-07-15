from __future__ import annotations

import io
from pathlib import Path

from fontTools.cffLib import CFFFontSet
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

from rebuild_cover_fonts import HEBREW_ALPHABET


OUT = Path("tmp/pdfs/visual-compare")
OUT.mkdir(parents=True, exist_ok=True)


def record_bounds(record):
    xs, ys = [], []
    for _op, args in record:
        for item in args:
            if isinstance(item, tuple):
                xs.append(float(item[0]))
                ys.append(float(item[1]))
    if not xs:
        return (0, 0, 1, 1)
    return min(xs), min(ys), max(xs), max(ys)


def sample_cubic(p0, p1, p2, p3, steps=18):
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        yield (
            mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0],
            mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1],
        )


def sample_quad(p0, p1, p2, steps=18):
    for i in range(1, steps + 1):
        t = i / steps
        mt = 1 - t
        yield (
            mt**2 * p0[0] + 2 * mt * t * p1[0] + t**2 * p2[0],
            mt**2 * p0[1] + 2 * mt * t * p1[1] + t**2 * p2[1],
        )


def draw_record(draw, record, box, fill=(20, 20, 20)):
    x0, y0, x1, y1 = record_bounds(record)
    width = max(x1 - x0, 1)
    height = max(y1 - y0, 1)
    bx, by, bw, bh = box
    scale = min(bw / width, bh / height) * 0.86
    ox = bx + bw / 2 - ((x0 + x1) / 2) * scale
    oy = by + bh / 2 + ((y0 + y1) / 2) * scale

    def tr(point):
        return (ox + point[0] * scale, oy - point[1] * scale)

    contours = []
    current = []
    current_point = None
    start_point = None
    for op, args in record:
        if op == "moveTo":
            if current:
                contours.append(current)
            current_point = args[0]
            start_point = args[0]
            current = [tr(current_point)]
        elif op == "lineTo":
            current_point = args[0]
            current.append(tr(current_point))
        elif op == "curveTo":
            p0 = current_point
            p1, p2, p3 = args
            for point in sample_cubic(p0, p1, p2, p3):
                current.append(tr(point))
            current_point = p3
        elif op == "qCurveTo":
            p0 = current_point
            points = list(args)
            if points[-1] is None:
                points[-1] = start_point
            for idx in range(len(points) - 1):
                p1, p2 = points[idx], points[idx + 1]
                for point in sample_quad(p0, p1, p2):
                    current.append(tr(point))
                p0 = p2
            current_point = points[-1]
        elif op == "closePath":
            if start_point is not None:
                current.append(tr(start_point))
            if current:
                contours.append(current)
            current = []
            current_point = None
            start_point = None
    if current:
        contours.append(current)
    for contour in contours:
        if len(contour) > 2:
            draw.polygon(contour, fill=fill)


def ttf_record(font, glyph_name):
    pen = RecordingPen()
    font.getGlyphSet()[glyph_name].draw(pen)
    return pen.value


def cff_record(cff, glyph_name):
    pen = RecordingPen()
    cff[0].CharStrings[glyph_name].draw(pen)
    return pen.value


def main():
    font_path = Path("assets/fonts/PDF-david-regular.ttf")
    jfont = TTFont(font_path)
    cmap = jfont["cmap"].getcmap(3, 1).cmap
    j_items = [(ch, ttf_record(jfont, cmap[ord(ch)])) for ch in HEBREW_ALPHABET if ord(ch) in cmap]

    cff_path = Path("tmp/pdfs/font-sources/gzec12825804/F8-TDavid-Normal.ttf")
    cff = CFFFontSet()
    cff.decompile(io.BytesIO(cff_path.read_bytes()), None)
    v_items = [(name, cff_record(cff, name)) for name in cff[0].charset if name != ".notdef"]

    cell_w, cell_h = 92, 104
    cols = 8
    rows = 2 + (len(j_items) + cols - 1) // cols + (len(v_items) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    draw.text((8, 8), "JDavid rebuilt: known Hebrew mapping", fill=(0, 0, 0), font=font)
    y = 28
    for idx, (label, record) in enumerate(j_items):
        x = (idx % cols) * cell_w
        yy = y + (idx // cols) * cell_h
        draw.rectangle((x + 2, yy + 2, x + cell_w - 2, yy + cell_h - 2), outline=(220, 220, 220))
        draw.text((x + 6, yy + 6), label, fill=(0, 0, 0), font=font)
        draw_record(draw, record, (x + 8, yy + 22, cell_w - 16, cell_h - 28))

    start_y = y + ((len(j_items) + cols - 1) // cols) * cell_h + 22
    draw.text((8, start_y), "VTDavid-Normal CFF glyphs from gzec12825804/F8", fill=(0, 0, 0), font=font)
    y = start_y + 20
    for idx, (label, record) in enumerate(v_items):
        x = (idx % cols) * cell_w
        yy = y + (idx // cols) * cell_h
        draw.rectangle((x + 2, yy + 2, x + cell_w - 2, yy + cell_h - 2), outline=(220, 220, 220))
        draw.text((x + 6, yy + 6), label[:12], fill=(0, 0, 0), font=font)
        draw_record(draw, record, (x + 8, yy + 22, cell_w - 16, cell_h - 28), fill=(30, 30, 30))

    out = OUT / "jdavid-vs-vtdavid-glyphs.png"
    img.save(out)
    print(out)


if __name__ == "__main__":
    main()
