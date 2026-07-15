"""Build the three fixed cover templates used before editing starts."""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


PAGE_WIDTH = 432
PAGE_HEIGHT = 648
REFERENCE_WIDTH = 396
REFERENCE_HEIGHT = 612


def image_crop(reference: Image.Image, source_box: tuple[float, float, float, float]) -> Image.Image:
    x, y, width, height = source_box
    scale_x = reference.width / REFERENCE_WIDTH
    scale_y = reference.height / REFERENCE_HEIGHT
    left = round(x * scale_x)
    top = round((REFERENCE_HEIGHT - y - height) * scale_y)
    right = round((x + width) * scale_x)
    bottom = round((REFERENCE_HEIGHT - y) * scale_y)
    return reference.crop((left, top, right, bottom)).convert("RGB")


def draw_crop(
    overlay: canvas.Canvas,
    reference: Image.Image,
    source_box: tuple[float, float, float, float],
    target_box: tuple[float, float, float, float],
) -> None:
    crop = image_crop(reference, source_box)
    crop_bytes = io.BytesIO()
    crop.save(crop_bytes, format="PNG", optimize=True)
    crop_bytes.seek(0)
    overlay.drawImage(ImageReader(crop_bytes), *target_box, preserveAspectRatio=False, mask=None)


def draw_target_crop(
    overlay: canvas.Canvas,
    reference: Image.Image,
    target_box: tuple[float, float, float, float],
) -> None:
    x, y, width, height = target_box
    scale_x = reference.width / PAGE_WIDTH
    scale_y = reference.height / PAGE_HEIGHT
    crop = reference.crop(
        (
            round(x * scale_x),
            round((PAGE_HEIGHT - y - height) * scale_y),
            round((x + width) * scale_x),
            round((PAGE_HEIGHT - y) * scale_y),
        )
    ).convert("RGB")
    crop_bytes = io.BytesIO()
    crop.save(crop_bytes, format="PNG", optimize=True)
    crop_bytes.seek(0)
    overlay.drawImage(ImageReader(crop_bytes), *target_box, preserveAspectRatio=False, mask=None)


def merged_template(base_pdf: Path, draw_overlay, destination: Path) -> None:
    overlay_bytes = io.BytesIO()
    overlay = canvas.Canvas(overlay_bytes, pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)
    draw_overlay(overlay)
    overlay.save()
    overlay_bytes.seek(0)

    page = PdfReader(base_pdf).pages[0]
    page.merge_page(PdfReader(overlay_bytes).pages[0])
    writer = PdfWriter()
    writer.add_page(page)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output_file:
        writer.write(output_file)


def build(base_pdf: Path, frame_pdf: Path, pinchas_render: Path, output_dir: Path) -> None:
    reference = Image.open(pinchas_render)

    def without_honorific(overlay: canvas.Canvas) -> None:
        overlay.setFillColorRGB(1, 1, 1)
        overlay.rect(80, 394, 272, 18, stroke=0, fill=1)

    merged_template(base_pdf, without_honorific, output_dir / "cover-template-no-honorific.pdf")

    def historical(overlay: canvas.Canvas) -> None:
        for strip in (
            (36, 576, 360, 28),
            (36, 43, 360, 29),
            (36, 43, 28, 561),
            (369, 43, 28, 561),
        ):
            draw_target_crop(overlay, reference, strip)
        overlay.setFillColorRGB(1, 1, 1)
        overlay.rect(72, 326, 288, 136, stroke=0, fill=1)
        # Header and attribution are raster crops of the supplied PDF, so the
        # original subset fonts and exact spacing remain untouched.
        draw_crop(overlay, reference, (55, 505, 286, 35), (60, 550, 312, 27))
        draw_crop(overlay, reference, (70, 280, 256, 110), (74, 332, 284, 124))

    merged_template(base_pdf, historical, output_dir / "cover-template-historical.pdf")
    print("Created fixed no-honorific and historical preset templates")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_pdf", type=Path)
    parser.add_argument("frame_pdf", type=Path)
    parser.add_argument("pinchas_render", type=Path)
    parser.add_argument("output_dir", type=Path)
    arguments = parser.parse_args()
    build(arguments.base_pdf, arguments.frame_pdf, arguments.pinchas_render, arguments.output_dir)


if __name__ == "__main__":
    main()
