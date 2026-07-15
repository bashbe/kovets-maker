"""Extract the first-page book ornament from the reference PDF as SVG.

The PDF keeps the outer wavy frame and the inner rules as vector objects. This
script preserves those paths instead of tracing a bitmap.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pdfplumber


def number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def svg_path(segments: list[tuple]) -> str:
    commands: list[str] = []
    for segment in segments:
        operator = segment[0]
        if operator == "h":
            commands.append("Z")
            continue

        points = segment[1:]
        if operator in {"m", "l"}:
            x, y = points[0]
            commands.append(f"{operator.upper()} {number(x)} {number(y)}")
        elif operator == "c":
            values = " ".join(
                f"{number(x)} {number(y)}" for x, y in points
            )
            commands.append(f"C {values}")
        else:
            raise ValueError(f"Unsupported PDF path operator: {operator}")
    return " ".join(commands)


def extract(source: Path, destination: Path) -> None:
    with pdfplumber.open(source) as pdf:
        page = pdf.pages[0]
        curves = page.objects.get("curve", [])
        rectangles = page.objects.get("rect", [])

        if len(curves) < 2 or len(rectangles) < 3:
            raise RuntimeError("The expected first-page ornament was not found.")

        lines = [
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {number(page.width)} {number(page.height)}" '
            'role="img" aria-label="Ornement de couverture">',
            '  <g fill="currentColor" stroke="none" fill-rule="evenodd">',
        ]

        for curve in curves:
            if curve.get("fill"):
                lines.append(f'    <path d="{svg_path(curve["path"])}"/>')

        for rectangle in rectangles:
            if not rectangle.get("fill"):
                continue
            width = rectangle["x1"] - rectangle["x0"]
            height = rectangle["bottom"] - rectangle["top"]
            lines.append(
                '    <rect '
                f'x="{number(rectangle["x0"])}" '
                f'y="{number(rectangle["top"])}" '
                f'width="{number(width)}" height="{number(height)}"/>'
            )
        lines.append("  </g>")

        # The stroked copies keep the small original edge details crisp.
        lines.append(
            '  <g fill="none" stroke="currentColor" '
            'vector-effect="non-scaling-stroke">'
        )
        for curve in curves:
            if curve.get("stroke"):
                width = number(curve.get("linewidth", 0.2))
                lines.append(
                    f'    <path d="{svg_path(curve["path"])}" '
                    f'stroke-width="{width}"/>'
                )

        for rectangle in rectangles:
            if not rectangle.get("stroke"):
                continue
            width = rectangle["x1"] - rectangle["x0"]
            height = rectangle["bottom"] - rectangle["top"]
            lines.append(
                '    <rect '
                f'x="{number(rectangle["x0"])}" '
                f'y="{number(rectangle["top"])}" '
                f'width="{number(width)}" height="{number(height)}" '
                f'stroke-width="{number(rectangle.get("linewidth", 0.5))}"/>'
            )

        lines.extend(["  </g>", "</svg>", ""])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    extract(args.source, args.destination)


if __name__ == "__main__":
    main()
