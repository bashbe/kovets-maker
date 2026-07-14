"""Extract the untouched first page used as the PDF cover template."""

from pathlib import Path
import sys

from pypdf import PdfReader, PdfWriter


DEFAULT_SOURCE = Path(r"C:\Users\BCBen\Downloads\xdxU13773815.pdf")
OUTPUT = Path("assets/cover-template.pdf")


source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
reader = PdfReader(source)
writer = PdfWriter()
writer.add_page(reader.pages[0])

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
with OUTPUT.open("wb") as output_file:
    writer.write(output_file)

print(f"Created {OUTPUT} from page 1 of {source}")
