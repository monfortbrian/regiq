"""
Serves the RAG chain to the Chrome Extension via Server-Sent Events.

Run: uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from src.rag import RegIQ, format_context, format_source, SYSTEM_PROMPT
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="RegIQ", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = RegIQ(model="gpt-4o-mini", top_k=6)


class Question(BaseModel):
    question: str
    jurisdiction: str = "bnr"


@app.get("/health")
def health():
    return {"status": "ok", "ready": rag.is_ready}


@app.post("/ask")
def ask(body: Question):
    result = rag.ask(body.question)
    return {
        "answer": result["answer"],
        "sources": result["sources"],
    }


@app.post("/ask/stream")
async def ask_stream(body: Question):
    """Stream answer tokens as Server-Sent Events."""

    def generate():
        from langchain.prompts import ChatPromptTemplate

        rag._load()
        sources_docs = rag._retriever.invoke(body.question)
        context     = format_context(sources_docs)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{question}"),
        ])
        messages = prompt.format_messages(
            context=context,
            question=body.question,
        )

        # ── Stream tokens and accumulate full answer ───────────────────────
        full_text = ""
        for chunk in rag.llm.stream(messages):
            token = chunk.content
            if token:
                full_text += token
                yield f"data: {json.dumps({'token': token})}\n\n"

        # ── Only send citation chips if the answer actually cites a directive ──
        # Greetings, off-topic replies, and redirections get no chips.
        has_citation = "Directive" in full_text or "Article" in full_text

        sources = []
        if has_citation:
            seen = set()
            for doc in sources_docs:
                citation = format_source(doc)
                if citation not in seen:
                    seen.add(citation)
                    sources.append({
                        "citation": citation,
                        "preview": (
                            doc.page_content[:180] + "..."
                            if len(doc.page_content) > 180
                            else doc.page_content
                        ),
                    })

        yield f"data: {json.dumps({'sources': sources, 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )