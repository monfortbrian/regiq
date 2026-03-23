"""
Uses GPT-4o Vision to extract text from scanned BNR directive PDFs.

Run: python ocr_with_gpt4o.py

Processes all 15 scanned PDFs, saves extracted text to data/ocr_text/
Then run: python -m src.ingest  to rebuild the vector store.
"""

import os
import base64
import json
import io
from pathlib import Path
from typing import Optional

import pdfplumber
from pdf2image import convert_from_path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ─── Windows paths - Tesseract and Poppler locations ─────────────────────────
POPPLER_PATH = r"C:\poppler\poppler-25.12.0\Library\bin"

# ─── OpenAI client ────────────────────────────────────────────────────────────
client = OpenAI()

# ─── Paths ────────────────────────────────────────────────────────────────────
DIRECTIVES_DIR = Path("data/directives")
OCR_TEXT_DIR = Path("data/ocr_text")
OCR_TEXT_DIR.mkdir(parents=True, exist_ok=True)

# ─── All 15 scanned PDFs confirmed by check_pdfs.py ──────────────────────────
SCANNED_PDFS = [
    "d_00034_2023_compensation_framework_banks.pdf",
    "d_0025_2020_bnr_check_duplicate.pdf",
    "d_0025_2020_extended_lending_facility.pdf",
    "d_04_2018_treatment_collaterals_guarantees.pdf",
    "d_05_2012_customer_service_delivery.pdf",
    "d_05_2012_customer_service_delivery_appendix.pdf",
    "d_09_2018_lending_foreign_currency.pdf",
    "d_2500_2018_electronic_data_warehouse.pdf",
    "d_bnr_2020_economic_recovery_fund_covid19.pdf",
    "d_bnr_2021_characteristics_independent_director.pdf",
    "d_bnr_2023_shared_services.pdf",
    "d_bnr_activities_liquidity_norms_development_banks.pdf",
    "d_bnr_emergency_liquidity_facility.pdf",
    "d_bnr_private_banking_services.pdf",
    "d_O15_2019_confirm_title.pdf",
]

# ─── GPT-4o system prompt for OCR ─────────────────────────────────────────────
OCR_SYSTEM_PROMPT = """You are a precise document transcription assistant for central banking regulatory documents.
Extract ALL text from this page of a National Bank of Rwanda (BNR) directive exactly as written.

RULES:
1. Preserve all headings exactly: CHAPTER I, Article 1, Article 2, etc.
2. Preserve all numbers, amounts in FRW, percentages exactly
3. For tables: format each row as: TEMPLATE_NAME | Description | Frequency
4. Preserve article numbers and titles exactly
5. Do not add commentary, notes, or explanations
6. If a page is mostly blank or just a signature/stamp, output: [SIGNATURE PAGE]
7. Output ONLY the extracted text, nothing else"""


def pdf_page_to_base64(pdf_path: Path, page_num: int) -> Optional[str]:
    """Convert one PDF page to a base64 PNG image for GPT-4o Vision."""
    try:
        images = convert_from_path(
            str(pdf_path),
            first_page=page_num,
            last_page=page_num,
            dpi=200,
            fmt="PNG",
            poppler_path=r"C:\Program Files\poppler\poppler-25.12.0\Library\bin",

        )
        if not images:
            return None
        buffer = io.BytesIO()
        images[0].save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"    Error converting page {page_num}: {e}")
        return None


def ocr_page_with_gpt4o(image_b64: str, page_num: int) -> str:
    """Send one page image to GPT-4o Vision and get back the extracted text."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4000,
            messages=[
                {"role": "system", "content": OCR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Extract all text from page {page_num} of this BNR directive:",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                },
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[OCR ERROR on page {page_num}: {e}]"


def ocr_one_pdf(pdf_path: Path) -> str:
    """OCR a single scanned PDF. Saves result to data/ocr_text/filename.txt"""
    output_path = OCR_TEXT_DIR / (pdf_path.stem + ".txt")

    # Skip if already done
    if output_path.exists():
        size = output_path.stat().st_size
        print(f"  SKIP (already done, {size} bytes): {pdf_path.name}")
        return output_path.read_text(encoding="utf-8")

    # Count pages
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
    except Exception:
        total_pages = 15

    print(f"\n  [{pdf_path.name}] - {total_pages} pages")

    all_pages = []
    for page_num in range(1, total_pages + 1):
        print(f"    Page {page_num}/{total_pages} ... ", end="", flush=True)

        image_b64 = pdf_page_to_base64(pdf_path, page_num)
        if not image_b64:
            print("FAILED (could not convert to image)")
            all_pages.append(f"[PAGE {page_num}]\n[Could not extract]")
            continue

        text = ocr_page_with_gpt4o(image_b64, page_num)
        all_pages.append(f"[PAGE {page_num}]\n{text}")
        print(f"done ({len(text)} chars)")

    full_text = "\n\n".join(all_pages)
    output_path.write_text(full_text, encoding="utf-8")
    print(f"  Saved to: {output_path}")
    return full_text


def run_all():
    print("\n" + "=" * 55)
    print("  RegIQ - GPT-4o OCR Pipeline")
    print("  Processing 15 scanned BNR directives")
    print("=" * 55)

    total = len(SCANNED_PDFS)
    done = 0
    failed = []

    for i, filename in enumerate(SCANNED_PDFS, 1):
        pdf_path = DIRECTIVES_DIR / filename

        if not pdf_path.exists():
            print(f"\n  [{i}/{total}] MISSING: {filename}")
            failed.append(filename)
            continue

        print(f"\n  [{i}/{total}]", end="")
        try:
            ocr_one_pdf(pdf_path)
            done += 1
        except Exception as e:
            print(f"\n  ERROR on {filename}: {e}")
            failed.append(filename)

    print("\n" + "=" * 55)
    print(f"  Done: {done}/{total} directives OCR'd")
    if failed:
        print(f"  Failed: {len(failed)}")
        for f in failed:
            print(f"    - {f}")
    print("\n  Next step: python -m src.ingest")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    run_all()
