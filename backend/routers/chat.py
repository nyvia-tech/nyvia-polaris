from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langfuse.decorators import observe, langfuse_context
from services.embeddings import embed_query
from services.vector_store import search
from services.llm import ask

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str
    top_k: int = 5
    filters: dict | None = None


class SourceChunk(BaseModel):
    source: str
    score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


@router.post("/", response_model=ChatResponse)
@observe(name="rag-chat")
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    langfuse_context.update_current_trace(
        name="rag-chat",
        input=req.question,
        metadata={"top_k": req.top_k},
    )

    query_vector = embed_query(req.question)
    chunks = search(query_vector, top_k=req.top_k, filters=req.filters)

    if not chunks:
        langfuse_context.flush()
        return ChatResponse(
            answer="No tengo información sobre eso en la base de conocimiento de Nyvia.",
            sources=[],
        )

    answer = ask(req.question, chunks)
    sources = [
        SourceChunk(
            source=c.get("source", "desconocido"),
            score=round(c.get("score", 0), 4),
            text=c.get("text", "")[:300],
        )
        for c in chunks
    ]

    langfuse_context.update_current_trace(
        output=answer,
        metadata={
            "top_k": req.top_k,
            "num_sources": len(sources),
            "sources": [s.source for s in sources],
        },
    )

    langfuse_context.flush()
    return ChatResponse(answer=answer, sources=sources)
