"""
Run: python check_pdfs.py
Checks every directive PDF and reports whether text can be extracted.
"""

import pdfplumber
from pathlib import Path

DIRECTIVES_DIR = Path("data/directives")

pdfs = sorted(DIRECTIVES_DIR.glob("*.pdf"))

if not pdfs:
    print("No PDFs found in data/directives/")
    exit()

print(f"\nChecking {len(pdfs)} PDFs...\n")
print(f"{'File':<55} {'Pages':>5}  {'Chars p.1':>9}  Status")
print("-" * 85)

scanned = []
ok = []

for pdf_path in pdfs:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = len(pdf.pages)
            text = ""
            # Check first 3 pages
            for page in pdf.pages[:3]:
                t = page.extract_text()
                if t:
                    text += t
                    break

            chars = len(text.strip())
            if chars < 50:
                status = "SCANNED / NO TEXT"
                scanned.append(pdf_path.name)
            else:
                status = "OK"
                ok.append(pdf_path.name)

            print(f"{pdf_path.name:<55} {pages:>5}  {chars:>9}  {status}")

    except Exception as e:
        print(f"{pdf_path.name:<55}  ERROR: {e}")
        scanned.append(pdf_path.name)

print("-" * 85)
print(f"\nOK (text extractable):  {len(ok)}")
print(f"SCANNED (need OCR):     {len(scanned)}")

if scanned:
    print("\nPDFs that need OCR:")
    for f in scanned:
        print(f"  - {f}")
