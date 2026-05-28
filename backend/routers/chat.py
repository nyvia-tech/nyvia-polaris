from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context
from services.embeddings import embed_query
from services.vector_store import search
from services.llm import ask
from config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

_langfuse = Langfuse(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
)


class ChatRequest(BaseModel):
    question: str
    top_k: int = 8
    filters: dict | None = None


class SourceChunk(BaseModel):
    source: str
    score: float
    text: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    trace_id: str | None = None


class FeedbackRequest(BaseModel):
    trace_id: str
    value: int  # 1 = útil, 0 = no útil


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

    MIN_SCORE = 0.25
    HIGH_SCORE = 0.55

    query_vector = embed_query(req.question)
    chunks = search(query_vector, top_k=req.top_k, filters=req.filters)
    chunks = [c for c in chunks if c.get("score", 0) >= MIN_SCORE]

    trace_id = langfuse_context.get_current_trace_id()

    if not chunks:
        langfuse_context.flush()
        return ChatResponse(
            answer="No tengo esa información en la base de conocimiento de Nyvia.",
            sources=[],
            trace_id=trace_id,
        )

    low_confidence = not any(c.get("score", 0) >= HIGH_SCORE for c in chunks)
    answer = ask(req.question, chunks, low_confidence=low_confidence)
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
            "low_confidence": low_confidence,
        },
    )

    langfuse_context.flush()
    return ChatResponse(answer=answer, sources=sources, trace_id=trace_id)


@router.post("/feedback")
def feedback(req: FeedbackRequest):
    if req.value not in (0, 1):
        raise HTTPException(status_code=400, detail="El valor debe ser 0 o 1.")

    _langfuse.score(
        trace_id=req.trace_id,
        name="user-feedback",
        value=req.value,
        comment="útil" if req.value == 1 else "no útil",
    )
    _langfuse.flush()
    return {"ok": True}
