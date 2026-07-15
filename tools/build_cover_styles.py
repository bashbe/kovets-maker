"""Build the three cover styles and the three reusable Rabbi formula images.

The styles contain only fixed artwork.  The Rabbi formula is deliberately kept
outside the template so every formula can be used with every style.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


PAGE_WIDTH = 432
PAGE_HEIGHT = 648
RENDER_WIDTH = 2400
RENDER_HEIGHT = 3600


def pdf_box_to_pixels(box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    x, y, width, height = box
    sx = RENDER_WIDTH / PAGE_WIDTH
    sy = RENDER_HEIGHT / PAGE_HEIGHT
    return (
        round(x * sx),
        round((PAGE_HEIGHT - y - height) * sy),
        round((x + width) * sx),
        round((PAGE_HEIGHT - y) * sy),
    )


def white_box(image: Image.Image, box: tuple[float, float, float, float]) -> None:
    ImageDraw.Draw(image).rectangle(pdf_box_to_pixels(box), fill="white")


def crop_pdf(image: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    return image.crop(pdf_box_to_pixels(box)).convert("RGB")


def paste_kehot_logo(image: Image.Image, logo_path: Path) -> None:
    """Restore the Kehot logo at its original PDF scale without distortion."""
    # The source PDF places R54 at 45.70248 x 54.339 points on a 396 x 612
    # page.  Scale uniformly from the page height so the embedded bitmap keeps
    # its exact proportions on the 432 x 648 target page.
    source_logo = Image.open(logo_path).convert("RGB")
    target_height = 54.339 * (PAGE_HEIGHT / 612)
    target_width = target_height * (source_logo.width / source_logo.height)
    target_x = (PAGE_WIDTH - target_width) / 2
    target_y = 153.7794 * (PAGE_HEIGHT / 612)

    # Remove every pixel of the previously page-scaled logo before restoring
    # the source object itself.
    white_box(image, (184, 155, 64, 72))
    pixel_box = pdf_box_to_pixels((target_x, target_y, target_width, target_height))
    width = pixel_box[2] - pixel_box[0]
    height = pixel_box[3] - pixel_box[1]
    restored = source_logo.resize((width, height), Image.Resampling.LANCZOS)
    image.paste(restored, pixel_box[:2])


def save_style(image: Image.Image, stem: Path) -> None:
    preview = image.resize((1200, 1800), Image.Resampling.LANCZOS)
    preview.save(stem.with_suffix(".png"), optimize=True)

    pdf = canvas.Canvas(str(stem.with_suffix(".pdf")), pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)
    pdf.drawImage(ImageReader(image), 0, 0, PAGE_WIDTH, PAGE_HEIGHT, preserveAspectRatio=False, mask=None)
    pdf.showPage()
    pdf.save()


def save_trimmed_formula(image: Image.Image, destination: Path) -> None:
    """Remove blank source margins while retaining a small safe edge."""
    rgb = image.convert("RGB")
    grayscale = rgb.convert("L")
    ink_mask = grayscale.point(lambda value: 255 if value < 238 else 0)
    bounds = ink_mask.getbbox()
    if not bounds:
        raise ValueError(f"No formula ink found for {destination}")
    trimmed = rgb.crop(bounds)
    padding_x = max(12, round(trimmed.width * 0.025))
    padding_y = max(10, round(trimmed.height * 0.035))
    result = Image.new(
        "RGB",
        (trimmed.width + padding_x * 2, trimmed.height + padding_y * 2),
        "white",
    )
    result.paste(trimmed, (padding_x, padding_y))
    result.save(destination, optimize=True)


def normalized_formula(crop: Image.Image, destination: Path) -> None:
    save_trimmed_formula(crop, destination)


def build_clean_formula(hanochos: Image.Image, destination: Path) -> None:
    # Keep the exact original first/name and surname/location crops.  The lower
    # lines are brought directly under the name and the compact block is set a
    # little lower, eliminating the empty line left by the removed honorific.
    upper = crop_pdf(hanochos, (84, 411, 264, 48))
    lower = crop_pdf(hanochos, (126, 363, 180, 37))
    upper.thumbnail((940, 205), Image.Resampling.LANCZOS)
    lower.thumbnail((720, 140), Image.Resampling.LANCZOS)
    result = Image.new("RGB", (1000, 400), "white")
    upper_y = 48
    lower_y = upper_y + upper.height + 8
    result.paste(upper, ((1000 - upper.width) // 2, upper_y))
    result.paste(lower, ((1000 - lower.width) // 2, lower_y))
    save_trimmed_formula(result, destination)


def build(
    hanochos_path: Path,
    vaad_path: Path,
    kehot_path: Path,
    kehot_logo_path: Path,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    hanochos = Image.open(hanochos_path).convert("RGB").resize((RENDER_WIDTH, RENDER_HEIGHT))
    vaad = Image.open(vaad_path).convert("RGB").resize((RENDER_WIDTH, RENDER_HEIGHT))
    kehot = Image.open(kehot_path).convert("RGB").resize((RENDER_WIDTH, RENDER_HEIGHT))
    kehot_original = kehot.copy()

    # Preserve the common Hanochos bottom content while retaining the Kehot
    # frame itself on the sides and along the lower edge.
    bottom_box = pdf_box_to_pixels((70, 55, 292, 98))
    kehot.paste(hanochos.crop(bottom_box), bottom_box[:2])
    # Restore the original Kehot lower frame over the shared bottom content.
    frame_bottom_box = pdf_box_to_pixels((0, 0, 432, 68))
    kehot.paste(kehot_original.crop(frame_bottom_box), frame_bottom_box[:2])
    paste_kehot_logo(kehot, kehot_logo_path)

    hanochos_style = hanochos.copy()
    white_box(hanochos_style, (76, 357, 280, 104))
    save_style(hanochos_style, output_dir / "cover-style-hanochos")

    vaad_style = vaad.copy()
    white_box(vaad_style, (72, 333, 288, 94))
    save_style(vaad_style, output_dir / "cover-style-vaad")

    kehot_style = kehot.copy()
    white_box(kehot_style, (72, 305, 288, 94))
    save_style(kehot_style, output_dir / "cover-style-kehot")

    normalized_formula(crop_pdf(hanochos, (76, 357, 280, 104)), output_dir / "rebbe-formula-full.png")
    build_clean_formula(hanochos, output_dir / "rebbe-formula-clean.png")
    normalized_formula(crop_pdf(vaad, (72, 333, 288, 94)), output_dir / "rebbe-formula-shlita.png")
    print("Created three independent cover styles and three Rabbi formula images")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("hanochos_render", type=Path)
    parser.add_argument("vaad_render", type=Path)
    parser.add_argument("kehot_render", type=Path)
    parser.add_argument("kehot_logo", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    build(
        args.hanochos_render,
        args.vaad_render,
        args.kehot_render,
        args.kehot_logo,
        args.output_dir,
    )


if __name__ == "__main__":
    main()
