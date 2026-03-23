# RegIQ

**Regulatory IQ, grounded in official circulars/directives.**

RegIQ transforms central bank circular and directive texts into clear, usable answers. Ask a compliance question in plain language and receive a precise response with the exact source, directive number, article, and page.

Built for compliance officers, bank legal teams, and financial regulators across Rwanda, Kenya, Uganda, Burundi, DRC, Somalia, South Sudan and Tanzania.

---

## What it does

A compliance officer types: _"What's the penalty for late data submission?"_

RegIQ responds:

> Under Directive No. 2500/2018, Article 21 - banks face **500,000 FRW** for non-submission plus **50,000 FRW per day** of delay. Insurance brokers, MFIs, e-money issuers, and other supervised institutions face 100,000 FRW base penalty plus 10,000 FRW/day.

Every answer is cited. No guessing. No manual PDF search.

---

## Coverage

| Jurisdiction | Central Bank                             | Status                |
| ------------ | -----------------------------------------| --------------------  |
| Rwanda       | National Bank of Rwanda (BNR)            | Live - 19+ directives |
| Kenya        | Kenya Central Bank (CBK)                 | Coming soon           |
| Uganda       | Central Bank of Uganda (BOU)             | Coming soon           |
| Burundi      | Banque de la République du Burundi (BRB) | Coming soon           |
| DRC          | Banque Centrale du Congo (BCC)           | Coming soon           |
| Somalia      | Central Bank of Somalia (CBS)            | Coming soon           |
| South Sudan  | Bank of South Sudan (BSS)                | Coming soon           |
| Tanzania     | Bank of Tanzania (BOT)                   | Coming soon           |

The architecture is jurisdiction-agnostic. Adding a new country means ingesting its directive corpus - the retrieval and generation pipeline requires no changes.

---

## Architecture

```
Central bank PDFs → OCR → Article-level chunking
→ OpenAI embeddings → ChromaDB vector store
→ FastAPI streaming backend → Chrome Extension side panel
```

**Ingestion** - Each directive is parsed into article-level chunks with metadata: directive number, article number, article title, chapter, and page. Scanned PDFs (common across African central banks) are handled via OCR with table extraction preserved.

**Retrieval** - Maximum Marginal Relevance (MMR) retrieval selects diverse, non-redundant chunks across the corpus. Top 6 chunks per query.

**Generation** - GPT-4o-mini with a strict citation prompt. Every answer cites directive number, article, and specific requirements. Hallucination of regulatory numbers is structurally prevented.

**Delivery** - FastAPI streaming backend with Server-Sent Events. Chrome Extension side panel with jurisdiction switching, citation chips, and source preview.

---

## Stack

Python · FastAPI · LangChain · ChromaDB · OpenAI · Chrome Extensions Manifest V3

---

## Roadmap

- Kenya CBK circular corpus ingestion
- Burundi BRB circular corpus ingestion
- Uganda BOU directive corpus ingestion
- Tanzania BOT directive corpus ingestion
- Somalia  CBS directive corpus ingestion
- DRC BCC directive corpus ingestion
- South Sudan BSS directive corpus ingestion
- Multi-language query support (French, Kinyarwanda, Swahili, Lingala)

---

Built by [Monfort Brian N.](https://github.com/monfortbrian)
