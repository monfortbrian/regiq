"""
Serves the RAG chain to the Chrome Extension via streaming HTTP.

Run: uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
from src.rag import RegIQ
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
    from langchain_openai import ChatOpenAI
    from langchain.prompts import ChatPromptTemplate
    from src.rag import format_context

    def generate():
        rag._load()
        sources_docs = rag._retriever.invoke(body.question)
        context = format_context(sources_docs)

        from langchain.prompts import ChatPromptTemplate
        from src.rag import SYSTEM_PROMPT

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{question}"),
        ])
        messages = prompt.format_messages(
            context=context,
            question=body.question
        )

        for chunk in rag.llm.stream(messages):
            token = chunk.content
            if token:
                data = json.dumps({"token": token})
                yield f"data: {data}\n\n"

        # Send sources after answer
        from src.rag import format_source
        sources = []
        seen = set()
        for doc in sources_docs:
            citation = format_source(doc)
            if citation not in seen:
                seen.add(citation)
                sources.append({
                    "citation": citation,
                    "preview": doc.page_content[:180] + "..."
                    if len(doc.page_content) > 180
                    else doc.page_content,
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
