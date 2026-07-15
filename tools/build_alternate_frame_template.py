"""Replace the current cover frame with four high-resolution raster strips.

Render the supplied reference cover to the same aspect ratio first. Keeping
the replacement in narrow strips preserves every vector object in the centre
of the original template while avoiding transparent-PNG quirks in PDF readers.
"""

from __future__ import annotations

import argparse
import io
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


TARGET_WIDTH = 432
TARGET_HEIGHT = 648

# Coordinates use PDF points with an origin at the bottom left. Each strip is
# wide enough to erase the former ornament but stops before editable content.
STRIPS = (
    (36, 576, 360, 28),
    (36, 43, 360, 29),
    (36, 43, 28, 561),
    (369, 43, 28, 561),
)


def crop_for_pdf(image: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    x, y, width, height = box
    scale_x = image.width / TARGET_WIDTH
    scale_y = image.height / TARGET_HEIGHT
    left = round(x * scale_x)
    top = round((TARGET_HEIGHT - y - height) * scale_y)
    right = round((x + width) * scale_x)
    bottom = round((TARGET_HEIGHT - y) * scale_y)
    return image.crop((left, top, right, bottom))


def build(base_pdf: Path, rendered_frame: Path, destination: Path) -> None:
    reference = Image.open(rendered_frame).convert("RGB")
    if reference.width / reference.height != TARGET_WIDTH / TARGET_HEIGHT:
        reference = reference.resize((2400, 3600), Image.Resampling.LANCZOS)

    overlay_bytes = io.BytesIO()
    overlay = canvas.Canvas(overlay_bytes, pagesize=(TARGET_WIDTH, TARGET_HEIGHT), pageCompression=1)
    for box in STRIPS:
        strip = crop_for_pdf(reference, box)
        strip_bytes = io.BytesIO()
        strip.save(strip_bytes, format="PNG", optimize=True)
        strip_bytes.seek(0)
        overlay.drawImage(ImageReader(strip_bytes), *box, preserveAspectRatio=False, mask=None)
    overlay.save()
    overlay_bytes.seek(0)

    base_page = PdfReader(base_pdf).pages[0]
    base_page.merge_page(PdfReader(overlay_bytes).pages[0])
    writer = PdfWriter()
    writer.add_page(base_page)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output_file:
        writer.write(output_file)
    print(f"Created {destination} from {base_pdf} and {rendered_frame}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_pdf", type=Path)
    parser.add_argument("rendered_frame", type=Path)
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    build(arguments.base_pdf, arguments.rendered_frame, arguments.destination)


if __name__ == "__main__":
    main()
