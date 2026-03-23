"""
Processes BNR directive PDFs into article-level chunks with full metadata.
Run once: python -m src.ingest
"""

import os
import re
import json
from pathlib import Path
from typing import Optional
import pdfplumber
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# ─── Paths ────────────────────────────────────────────────────────────────────
DIRECTIVES_DIR = Path("data/directives")
PROCESSED_DIR = Path("data/processed")
CHROMA_DIR = Path("data/chroma_db")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# ─── Directive metadata registry ──────────────────────────────────────────────
# Add one entry per PDF file you place in data/directives/
# filename: the exact PDF filename (without path)
# number: official directive number for citations
# title: short human-readable title
# year: year issued
# language: en or fr
# applies_to: list of institution types it governs

DIRECTIVE_REGISTRY: dict = {

    "d_05_2012_customer_service_delivery.pdf": {
        "number":     "No. 05/2012",
        "title":      "Customer Service Delivery in Financial Institutions",
        "year":       2012,
        "language":   "en",
        "applies_to": ["banks", "microfinance", "insurers",
                       "all financial institutions"],
    },
    "d_05_2012_customer_service_delivery_appendix.pdf": {
        "number":     "No. 05/2012 (Appendix)",
        "title":      "Appendix - Customer Service Delivery in Financial Institutions",
        "year":       2012,
        "language":   "en",
        "applies_to": ["banks", "microfinance", "insurers",
                       "all financial institutions"],
    },
    "d_bnr_emergency_liquidity_facility.pdf": {
        "number":     "BNR Emergency Liquidity Facility Directive",
        "title":      "Emergency Liquidity Facility",
        "year":       2018,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_bnr_activities_liquidity_norms_development_banks.pdf": {
        "number":     "BNR Development Banks Directive",
        "title":      "Activities and Liquidity Norms for Development Banks",
        "year":       2015,
        "language":   "en",
        "applies_to": ["development banks"],
    },
    "d_01_2018_computation_liquidity_ratios.pdf": {
        "number":     "No. 01/2018",
        "title":      "Computation of the Liquidity Ratios",
        "year":       2018,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_02_2018_capital_charge_credit_market_operational_risk.pdf": {
        "number":     "No. 02/2018",
        "title":      "Computation of Capital Charge for Credit, Market and Operational Risk",
        "year":       2018,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_03_2018_internal_capital_adequacy_assessment.pdf": {
        "number":     "No. 03/2018",
        "title":      "Internal Capital Adequacy Assessment Process (ICAAP)",
        "year":       2018,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_04_2018_treatment_collaterals_guarantees.pdf": {
        "number":     "No. 04/2018",
        "title":      "Treatment of Collaterals and Guarantees by Banks",
        "year":       2018,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_09_2018_lending_foreign_currency.pdf": {
        "number":     "No. 09/2018",
        "title":      "Lending in Foreign Currency",
        "year":       2018,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_2500_2018_electronic_data_warehouse.pdf": {
        "number":     "No. 2500/2018",
        "title":      "Electronic Data Warehouse Reporting Requirements",
        "year":       2018,
        "language":   "en",
        "applies_to": ["banks", "insurers", "microfinance",
                       "pension schemes", "e-money issuers",
                       "forex bureaus", "credit bureaus",
                       "remittance providers", "switch providers"],
    },
    "d_O15_2019_confirm_title.pdf": {
        "number":     "No. O15/2019",
        "title":      "Directive No. O15/2019",
        "year":       2019,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_0025_2020_extended_lending_facility.pdf": {
        "number":     "No. 0025/2020",
        "title":      "Operationalisation of the Extended Lending Facility",
        "year":       2020,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_0025_2020_bnr_check_duplicate.pdf": {
        "number":     "No. 0025/2020 (Companion)",
        "title":      "National Bank of Rwanda Extended Lending Facility",
        "year":       2020,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_bnr_2020_economic_recovery_fund_covid19.pdf": {
        "number":     "BNR Economic Recovery Fund 2020",
        "title":      "Economic Recovery Fund - COVID-19",
        "year":       2020,
        "language":   "en",
        "applies_to": ["banks", "microfinance",
                       "all financial institutions"],
    },
    "d_bnr_2021_characteristics_independent_director.pdf": {
        "number":     "BNR Independent Director Directive 2021",
        "title":      "Characteristics of an Independent Director",
        "year":       2021,
        "language":   "en",
        "applies_to": ["banks", "financial holdings"],
    },
    "d_4230_2022_recovery_plan_banks.pdf": {
        "number":     "No. 4230/2022",
        "title":      "Minimum Requirements of the Recovery Plan for Banks",
        "year":       2022,
        "language":   "en",
        "applies_to": ["banks", "financial holdings"],
    },
    "d_00034_2023_compensation_framework_banks.pdf": {
        "number":     "No. 00034/2023",
        "title":      "Compensation Framework for Banks",
        "year":       2023,
        "language":   "en",
        "applies_to": ["banks"],
    },
    "d_bnr_2023_shared_services.pdf": {
        "number":     "BNR Shared Services Directive 2023",
        "title":      "Shared Services",
        "year":       2023,
        "language":   "en",
        "applies_to": ["banks", "financial institutions"],
    },
    "d_bnr_private_banking_services.pdf": {
        "number":     "BNR Private Banking Services Directive",
        "title":      "Private Banking Services",
        "year":       2019,
        "language":   "en",
        "applies_to": ["banks"],
    },
}

# ─── Article pattern detection ────────────────────────────────────────────────
ARTICLE_PATTERNS = [
    r"^Article\s+\d+[:\s]",
    r"^ARTICLE\s+\d+[:\s]",
    r"^Art\.\s*\d+[:\s]",
]

CHAPTER_PATTERNS = [
    r"^CHAPTER\s+[IVX]+[:\s]",
    r"^Chapter\s+[IVX\d]+[:\s]",
]


def is_article_header(line: str) -> bool:
    return any(re.match(p, line.strip()) for p in ARTICLE_PATTERNS)


def is_chapter_header(line: str) -> bool:
    return any(re.match(p, line.strip()) for p in CHAPTER_PATTERNS)


def extract_article_number(line: str) -> Optional[str]:
    """Extract 'Article 3' from 'Article 3: Governance structure'"""
    m = re.match(r"(?:Article|ARTICLE|Art\.)\s*(\d+)", line.strip())
    return f"Article {m.group(1)}" if m else None


def extract_article_title(line: str) -> str:
    """Extract title after the colon in 'Article 3: Governance structure'"""
    parts = re.split(r"[:-–]", line, maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else line.strip()


# ─── Table extraction ─────────────────────────────────────────────────────────
def extract_tables_from_page(page, directive_meta: dict, page_num: int) -> list[Document]:
    """
    Convert each table row into a standalone text chunk.
    This makes template/frequency queries work precisely.
    """
    docs = []
    tables = page.extract_tables()
    for table in tables:
        if not table or len(table) < 2:
            continue
        # Detect header row
        headers = [str(h).strip() if h else "" for h in table[0]]
        is_template_table = any(
            h.lower() in ("template name", "template_name", "s/n", "sn")
            for h in headers
        )
        if not is_template_table:
            continue

        # Find column indices
        try:
            name_col = next(i for i, h in enumerate(headers)
                            if "template" in h.lower() and "name" in h.lower())
            desc_col = next(i for i, h in enumerate(headers)
                            if "description" in h.lower())
            freq_col = next(i for i, h in enumerate(headers)
                            if "frequency" in h.lower())
        except StopIteration:
            continue  # Table structure not recognised

        # Detect institution type from surrounding context
        page_text = page.extract_text() or ""
        institution = _detect_institution(page_text)

        for row in table[1:]:
            if not row or not row[name_col]:
                continue
            template_name = str(row[name_col]).strip()
            description = str(row[desc_col]).strip() if len(
                row) > desc_col else ""
            frequency = str(row[freq_col]).strip() if len(
                row) > freq_col else ""

            if not template_name or template_name.lower() in ("s/n", "sn", ""):
                continue

            text = (
                f"Template {template_name} ({description}) "
                f"must be submitted by {institution} "
                f"with {frequency} frequency. "
                f"Source: Directive {directive_meta['number']}, "
                f"Page {page_num}."
            )

            docs.append(Document(
                page_content=text,
                metadata={
                    "directive_number": directive_meta["number"],
                    "directive_title":  directive_meta["title"],
                    "year":             directive_meta["year"],
                    "language":         directive_meta["language"],
                    "applies_to":       ", ".join(directive_meta["applies_to"]),
                    "chunk_type":       "table_row",
                    "template_name":    template_name,
                    "frequency":        frequency.lower(),
                    "institution_type": institution,
                    "page":             page_num,
                    "article":          "Article 3",
                    "article_title":    "Data submission templates",
                }
            ))
    return docs


def _detect_institution(text: str) -> str:
    text_lower = text.lower()
    if "microfinance" in text_lower:
        return "microfinance institutions"
    if "insurer" in text_lower:
        return "insurers"
    if "pension" in text_lower:
        return "pension schemes"
    if "e-money" in text_lower or "emi" in text_lower:
        return "e-money issuers"
    if "forex" in text_lower:
        return "forex bureaus"
    if "credit bureau" in text_lower:
        return "credit bureaus"
    if "remittance" in text_lower:
        return "remittance providers"
    if "switch" in text_lower:
        return "switch providers"
    return "banks"


# ─── Article-level text chunking ──────────────────────────────────────────────
def chunk_by_article(
    pages_text: list[tuple[int, str]],
    directive_meta: dict
) -> list[Document]:
    """
    Split full directive text into one Document per Article.
    Falls back to page-level chunks if no articles found.
    """
    full_text = "\n".join(
        f"[PAGE {pnum}]\n{text}" for pnum, text in pages_text)
    lines = full_text.split("\n")

    chunks: list[Document] = []
    current_article = None
    current_article_num = None
    current_article_ttl = None
    current_chapter = "General Provisions"
    current_page = 1
    buffer: list[str] = []

    def flush():
        nonlocal buffer, current_article, current_article_num, current_article_ttl
        if not buffer or not current_article:
            return
        text = "\n".join(buffer).strip()
        if len(text) < 40:
            buffer = []
            return
        chunks.append(Document(
            page_content=text,
            metadata={
                "directive_number":  directive_meta["number"],
                "directive_title":   directive_meta["title"],
                "year":              directive_meta["year"],
                "language":          directive_meta["language"],
                "applies_to":        ", ".join(directive_meta["applies_to"]),
                "chunk_type":        "article",
                "article":           current_article_num or current_article,
                "article_title":     current_article_ttl or "",
                "chapter":           current_chapter,
                "page":              current_page,
            }
        ))
        buffer = []

    for line in lines:
        # Track page numbers
        page_match = re.match(r"^\[PAGE (\d+)\]$", line)
        if page_match:
            current_page = int(page_match.group(1))
            continue

        # Track chapters
        if is_chapter_header(line):
            current_chapter = line.strip()

        # New article - flush previous
        if is_article_header(line):
            flush()
            current_article = line.strip()
            current_article_num = extract_article_number(line)
            current_article_ttl = extract_article_title(line)
            buffer = [line.strip()]
        else:
            if current_article:
                buffer.append(line)

    flush()

    # Fallback: whole-page chunks if no articles detected
    if not chunks:
        for pnum, text in pages_text:
            if len(text.strip()) < 40:
                continue
            chunks.append(Document(
                page_content=text.strip(),
                metadata={
                    "directive_number": directive_meta["number"],
                    "directive_title":  directive_meta["title"],
                    "year":             directive_meta["year"],
                    "language":         directive_meta["language"],
                    "applies_to":       ", ".join(directive_meta["applies_to"]),
                    "chunk_type":       "page",
                    "article":          f"Page {pnum}",
                    "article_title":    "",
                    "chapter":          "",
                    "page":             pnum,
                }
            ))
    return chunks


# ─── OCR text loader ──────────────────────────────────────────────────────────
OCR_TEXT_DIR = Path("data/ocr_text")


def load_ocr_text(pdf_path: Path):
    ocr_path = OCR_TEXT_DIR / (pdf_path.stem + ".txt")
    if not ocr_path.exists():
        return None
    content = ocr_path.read_text(encoding="utf-8")
    pages = []
    current_page = 1
    current_lines = []
    for line in content.split("\n"):
        if line.startswith("[PAGE "):
            if current_lines:
                pages.append((current_page, "\n".join(current_lines)))
                current_lines = []
            try:
                current_page = int(line.replace(
                    "[PAGE ", "").split("/")[0].replace("]", "").strip())
            except Exception:
                current_page += 1
        else:
            current_lines.append(line)
    if current_lines:
        pages.append((current_page, "\n".join(current_lines)))
    return pages if pages else None


# ─── PDF processor ────────────────────────────────────────────────────────────
def process_pdf(pdf_path: Path, directive_meta: dict) -> list[Document]:
    all_docs: list[Document] = []
    pages_text: list[tuple[int, str]] = []

    print(f"  Processing: {pdf_path.name}")

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages_text.append((page_num, text))
            table_docs = extract_tables_from_page(
                page, directive_meta, page_num)
            all_docs.extend(table_docs)

    total_chars = sum(len(t) for _, t in pages_text)

    if total_chars < 200:
        ocr_pages = load_ocr_text(pdf_path)
        if ocr_pages:
            pages_text = ocr_pages
            print(f"    Using OCR text ({len(ocr_pages)} pages)")
        else:
            print(f"    No text and no OCR file found - skipping")

    article_docs = chunk_by_article(pages_text, directive_meta)
    all_docs.extend(article_docs)
    print(
        f"    Total chunks: {len(all_docs)} ({len(article_docs)} article + {len(all_docs) - len(article_docs)} table rows)")

    return all_docs

# ─── Main ingestion ────────────────────────────────────────────────────────────


def ingest_all():
    print("\n═══ RegIQ Ingestion Pipeline ═══\n")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    all_docs: list[Document] = []

    pdf_files = list(DIRECTIVES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"⚠  No PDFs found in {DIRECTIVES_DIR}/")
        print("   Place your BNR directive PDFs there and re-run.")
        return

    for pdf_path in sorted(pdf_files):
        meta = DIRECTIVE_REGISTRY.get(pdf_path.name)
        if not meta:
            print(f"⚠  No registry entry for {pdf_path.name} - skipping.")
            print(f"   Add it to DIRECTIVE_REGISTRY in src/ingest.py")
            continue

        docs = process_pdf(pdf_path, meta)
        all_docs.extend(docs)

    if not all_docs:
        print("No documents processed.")
        return

    print(f"\nTotal chunks across all directives: {len(all_docs)}")
    print("Building vector store...")

    vectorstore = Chroma.from_documents(
        documents=all_docs,
        embedding=embeddings,
        persist_directory=str(CHROMA_DIR),
        collection_name="bnr_directives",
    )

    print(f"✓ Vector store saved to {CHROMA_DIR}")
    print(f"✓ {len(all_docs)} chunks indexed\n")

    # Save processing summary
    summary = {
        "total_chunks": len(all_docs),
        "directives_processed": [p.name for p in pdf_files
                                 if p.name in DIRECTIVE_REGISTRY],
        "chunk_types": {
            "article": sum(1 for d in all_docs if d.metadata.get("chunk_type") == "article"),
            "table_row": sum(1 for d in all_docs if d.metadata.get("chunk_type") == "table_row"),
            "page": sum(1 for d in all_docs if d.metadata.get("chunk_type") == "page"),
        }
    }
    with open(PROCESSED_DIR / "ingestion_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("Summary:", json.dumps(summary, indent=2))


if __name__ == "__main__":
    ingest_all()
