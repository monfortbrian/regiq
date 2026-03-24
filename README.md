# RegIQ

**Regulatory intelligence for East African financial institutions.**

RegIQ turns central bank directives and circulars into precise, cited answers. Ask a compliance question and receive a response with the exact directive number, article, and page; the same level of precision a senior compliance counsel would provide, in seconds.

Built for compliance officers, bank legal teams, internal audit teams, and financial regulators across East and Central Africa.

---

## What it does

> _"What's the penalty for late data submission?"_

**RegIQ responds:**

> Under Directive No. 2500/2018, Article 21 - banks face **500,000 FRW** for non-submission plus **50,000 FRW per day** of delay. MFIs, e-money issuers, insurance brokers, and other supervised institutions face 100,000 FRW base penalty plus 10,000 FRW/day.

Every answer is cited. Every citation is traceable to its source article and page.

---

## Coverage

| Jurisdiction | Central Bank                             | Status                |
| ------------ | ---------------------------------------- | --------------------- |
| Rwanda       | National Bank of Rwanda (BNR)            | Live - 19+ directives |
| Kenya        | Central Bank of Kenya (CBK)              | Coming soon           |
| Uganda       | Bank of Uganda (BOU)                     | Coming soon           |
| Burundi      | Banque de la République du Burundi (BRB) | Coming soon           |
| DRC          | Banque Centrale du Congo (BCC)           | Coming soon           |
| Somalia      | Central Bank of Somalia (CBS)            | Coming soon           |
| South Sudan  | Bank of South Sudan (BSS)                | Coming soon           |
| Tanzania     | Bank of Tanzania (BOT)                   | Coming soon           |

The architecture is jurisdiction-agnostic. Adding a new country requires only ingesting its directive corpus - the retrieval and generation pipeline is unchanged.

---

## Architecture

```
Central bank PDFs
  → OCR pipeline (scanned document handling)
  → Article-level chunking with full metadata
  → Vector embeddings
  → ChromaDB retrieval
  → GPT-4o-mini generation with citation enforcement
  → FastAPI streaming backend
  → Chrome Extension side panel
```

**Ingestion** processes each directive into article-level chunks carrying directive number, article number, article title, chapter, and page as metadata. Scanned PDFs, common across African central bank websites are handled automatically with table extraction preserved.

**Retrieval** uses Maximum Marginal Relevance to surface diverse, non-redundant chunks across the full corpus.

**Generation** enforces citation on every response. Directive numbers, article references, FRW amounts, and template codes are structurally protected from fabrication.

**Delivery** streams token-by-token via server-Sent Events to a Chrome side panel with jurisdiction switching, citation chips, and source drawer.

**Multilingual** responds in the language of the question. English, French, Kinyarwanda, Swahili, Lingala, Kirundi supported. Technical codes and directive references are preserved in original form across all languages.

---

## Stack

Python 3.11 · FastAPI · LangChain · ChromaDB · OpenAI · Docker · Chrome Extensions Manifest V3

---

## Docker

```bash
docker pull monfortbrian/regiq-api:latest
```

API image: [hub.docker.com/r/monfortbrian/regiq-api](https://hub.docker.com/r/monfortbrian/regiq-api)

---

## Roadmap

- Kenya CBK corpus ingestion
- Uganda BOU corpus ingestion
- Burundi BRB corpus ingestion (French)
- DRC BCC corpus ingestion (French)
- Compliance gap checker - upload a bank policy, get a gap report against BNR directives

---

Built by [Monfort Brian N.](https://github.com/monfortbrian)
