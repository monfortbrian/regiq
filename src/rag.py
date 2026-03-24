"""
Retrieval-Augmented Generation with article-level citation formatting.
"""

from pathlib import Path
from typing import Optional
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import Document
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = Path("data/chroma_db")

# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are RegIQ, a regulatory intelligence assistant for the National Bank of Rwanda (BNR).
You have deep knowledge of BNR directives governing banks, insurers, microfinance institutions, pension schemes, e-money issuers, forex bureaus, and other supervised financial entities in Rwanda.

Your role is to answer compliance questions from bank officers, compliance teams, and regulators with precision and authority.

RESPONSE RULES:
1. Always cite the exact Directive number, Article number, and Article title when referencing a rule.
2. Use the citation format: "Under Directive [Number], [Article]: [what it says]"
3. For template/data submission questions: list the specific template names and codes.
4. For deadline questions: state exact times and conditions.
5. For penalty questions: state exact amounts in FRW.
6. Be concise but complete - no filler, no hedging, no "I think".
7. If a question spans multiple directives or articles, cite all of them.
8. End with a practical note if it adds value (e.g., what to do next, what to watch out for).
9. If someone greets you (hello, hi, bonjour, etc.) respond warmly and briefly introduce what you do.
   Example: "Hello! I'm RegIQ, I answer compliance questions about BNR directives with precise citations. Ask me anything about submission requirements, penalties, governance, or recovery planning."
10. LANGUAGE DETECTION AND RESPONSE RULE - non-negotiable:
    Step 1: Identify the language of the question.
    Common patterns:
      - "Quels", "Les banques", "Quelle est" → French
      - "Ni izihe", "Ni iki", "Ni gute" → Kinyarwanda
      - "Ba banque", "basengeli", "mokolo", "nini" → Lingala
      - "Ni nini", "Benki", "lazima" → Swahili
      - "Ni iki", "Amategeko" → Kirundi
    Step 2: Build the complete factually accurate answer using the directive context.
    Step 3: Translate the complete answer into the detected language.

    STRICT RULES for translation:
    - Keep ALL template codes exactly: BRANCHINFO, FRAUDTXN, GLCODES etc.
    - Keep ALL directive references exactly: No. 2500/2018, Article 3 etc.
    - Keep ALL amounts exactly: 500,000 FRW, 50,000 FRW etc.
    - Keep technical banking terms in English or use standard local banking term
    - NEVER redirect a legitimate compliance question just because it is in Lingala,
      Kinyarwanda, Swahili or Kirundi. These are valid working languages.
    - If you cannot translate with confidence, answer in French (lingua franca
      for DRC/Burundi) or English rather than giving a wrong or vague answer.
11. If the question is clearly unrelated to financial regulation, gently redirect in the
    same language the user wrote in:
    "I specialize in East African central bank directives/circulars. Try asking about submission templates, compliance deadlines, penalties, or governance requirements."
12. Never fabricate directive numbers, article numbers, or specific requirements.
13. Never show citation sources for greetings or off-topic redirections.

TONE: Professional, direct, authoritative - like a senior compliance counsel, not a chatbot.

CONTEXT FROM BNR DIRECTIVES:
{context}"""

HUMAN_PROMPT = "{question}"


# ─── Citation formatter ───────────────────────────────────────────────────────
def format_source(doc: Document) -> str:
    """Format a single source document into a citation line."""
    m = doc.metadata
    directive = m.get("directive_number", "Unknown Directive")
    title = m.get("directive_title",  "")
    article = m.get("article",          "")
    art_title = m.get("article_title",    "")
    page = m.get("page",             "")
    chunk_type = m.get("chunk_type",      "article")

    if chunk_type == "table_row":
        template = m.get("template_name",    "")
        freq = m.get("frequency",        "")
        inst = m.get("institution_type", "")
        return (f"Directive {directive} - {title} | "
                f"Table: {template} | {inst} | {freq} | p.{page}")

    art_display = f"{article}: {art_title}" if art_title else article
    return f"Directive {directive} - {title} | {art_display} | p.{page}"


def format_context(docs: list[Document]) -> str:
    """Combine retrieved chunks into a context block with source labels."""
    parts = []
    for i, doc in enumerate(docs, 1):
        source = format_source(doc)
        parts.append(f"[SOURCE {i}] {source}\n{doc.page_content}")
    return "\n\n".join(parts)


# ─── RegIQ RAG chain ──────────────────────────────────────────────────────────
class RegIQ:
    def __init__(self, model: str = "gpt-4o-mini", top_k: int = 6):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.top_k = top_k
        self._vectorstore: Optional[Chroma] = None
        self._retriever = None
        self._chain = None

    def _load(self):
        if self._vectorstore is not None:
            return
        if not CHROMA_DIR.exists():
            raise FileNotFoundError(
                f"Vector store not found at {CHROMA_DIR}. "
                "Run: python -m src.ingest"
            )
        self._vectorstore = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=self.embeddings,
            collection_name="bnr_directives",
        )
        self._retriever = self._vectorstore.as_retriever(
            search_type="mmr",              # Maximum marginal relevance - diversity
            search_kwargs={"k": self.top_k, "fetch_k": 20},
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human",  HUMAN_PROMPT),
        ])
        self._chain = (
            {
                "context":  self._retriever | format_context,
                "question": RunnablePassthrough(),
            }
            | prompt
            | self.llm
            | StrOutputParser()
        )

    def ask(self, question: str) -> dict:
        """
        Ask a compliance question.
        Returns {"answer": str, "sources": list[dict]}
        """
        self._load()

        # Retrieve sources for display
        sources_docs = self._retriever.invoke(question)

        # Run the full chain
        answer = self._chain.invoke(question)

        # Format sources for UI
        sources = []
        seen = set()
        for doc in sources_docs:
            citation = format_source(doc)
            if citation not in seen:
                seen.add(citation)
                sources.append({
                    "citation": citation,
                    "preview":  doc.page_content[:200] + "..."
                    if len(doc.page_content) > 200
                    else doc.page_content,
                    "metadata": doc.metadata,
                })

        return {"answer": answer, "sources": sources}

    def ask_stream(self, question: str):
        """Stream the answer token by token (for Streamlit st.write_stream)."""
        self._load()
        sources_docs = self._retriever.invoke(question)
        context = format_context(sources_docs)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human",  HUMAN_PROMPT),
        ])
        messages = prompt.format_messages(context=context, question=question)

        for chunk in self.llm.stream(messages):
            yield chunk.content

        return sources_docs

    @property
    def is_ready(self) -> bool:
        return CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir())

    def get_stats(self) -> dict:
        """Return vector store stats for the UI."""
        self._load()
        count = self._vectorstore._collection.count()
        return {"total_chunks": count}
