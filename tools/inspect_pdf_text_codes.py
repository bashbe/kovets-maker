from pathlib import Path

from pypdf import PdfReader
from pypdf.generic import ContentStream


PDF = Path(r"C:\Users\BCBen\Downloads\xdxU13773815.pdf")


def raw_hex(value):
    if isinstance(value, (int, float)):
        return value
    return value.original_bytes.hex()


reader = PdfReader(PDF)
content = ContentStream(reader.pages[0].get_contents(), reader)
font = ""
text_matrix = None

for operands, operator in content.operations:
    if operator == b"Tf":
        font = str(operands[0])
    elif operator == b"Tm":
        text_matrix = tuple(float(value) for value in operands)
    elif operator == b"Tj":
        print(font, text_matrix, operator.decode(), raw_hex(operands[0]))
    elif operator == b"TJ":
        print(font, text_matrix, operator.decode(), [raw_hex(item) for item in operands[0]])
