"""
Translates French BNR directives to English using GPT-4o,
preserving article structure, directive numbers, and legal precision.

Usage:
  python scripts/translate_directive.py data/directives/directive_fr.pdf

Output:
  data/directives/directive_fr_translated.pdf  (text saved as .txt)
"""

import sys
import re
from pathlib import Path
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

TRANSLATION_SYSTEM = """You are a professional legal translator specializing in central banking regulation and financial law.
You translate French regulatory directives from the National Bank of Rwanda (BNR / Banque Nationale du Rwanda) into English.

TRANSLATION RULES:
1. Preserve all Article numbers exactly (Article 1, Article 2, etc.)
2. Preserve all Chapter headings exactly (CHAPTER I, CHAPTER II, etc.)
3. Preserve all directive numbers exactly (Directive No. 2500/2018, etc.)
4. Preserve all template names, codes, and amounts exactly (BRANCHINFO, FRAUDTXN, 500,000 FRW, etc.)
5. Translate legal terms precisely - use standard central banking English terminology
6. Do not add commentary, notes, or explanations
7. Maintain paragraph structure exactly
8. Output only the translated text, nothing else"""


def translate_page(text: str, page_num: int) -> str:
    """Translate one page of French directive text."""
    if not text.strip():
        return ""

    print(f"  Translating page {page_num}...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": TRANSLATION_SYSTEM},
            {"role": "user",   "content": f"Translate this BNR directive page:\n\n{text}"}
        ],
        temperature=0,
        max_tokens=2000,
    )
    return response.choices[0].message.content


def translate_directive(pdf_path: Path) -> Path:
    """
    Translate a French directive PDF to English.
    Saves translated text to a .txt file (which ingest.py can read directly).
    """
    output_path = pdf_path.parent / (pdf_path.stem + "_en_translated.txt")

    print(f"\nTranslating: {pdf_path.name}")
    print(f"Output: {output_path.name}\n")

    translated_pages = []

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                translated = translate_page(text, page_num)
                translated_pages.append(
                    f"[PAGE {page_num}/{total_pages}]\n{translated}")
            else:
                translated_pages.append(
                    f"[PAGE {page_num}/{total_pages}]\n[No text content]")

    full_translation = "\n\n".join(translated_pages)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_translation)

    print(f"\n✓ Translation complete: {output_path}")
    print(f"  Pages translated: {total_pages}")
    print(f"  Output size: {len(full_translation):,} characters")

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/translate_directive.py <path_to_french_pdf>")
        print("Example: python scripts/translate_directive.py data/directives/directive_fr.pdf")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    translate_directive(pdf_path)
