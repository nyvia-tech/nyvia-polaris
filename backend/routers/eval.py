from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langfuse import observe, get_client
from services.embeddings import embed_query
from services.vector_store import search
from services.llm import ask, NO_INFO_ANSWER
from services.evaluator import judge_groundedness, judge_relevance

router = APIRouter(prefix="/eval", tags=["eval"])


class EvalRequest(BaseModel):
    question: str
    top_k: int = 5


class EvalResponse(BaseModel):
    question: str
    rag_answer: str
    sources: list[str]
    groundedness: dict  # score, verdict, unsupported_claims
    relevance: dict     # score, verdict, missing_aspects


@router.post("/", response_model=EvalResponse)
@observe(name="rag-eval")
def evaluate(req: EvalRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    get_client().update_current_trace(
        name="rag-eval",
        input=req.question,
    )

    query_vector = embed_query(req.question)
    chunks = search(query_vector, top_k=req.top_k)

    if not chunks:
        return EvalResponse(
            question=req.question,
            rag_answer="No tengo información sobre eso en la base de conocimiento de Nyvia.",
            sources=[],
            groundedness={"score": 0, "verdict": "Sin contexto para evaluar.", "unsupported_claims": "N/A"},
            relevance={"score": 0, "verdict": "Sin respuesta para evaluar.", "missing_aspects": "N/A"},
        )

    rag_answer = ask(req.question, chunks)
    source_names = list(dict.fromkeys(c.get("source", "") for c in chunks))

    if NO_INFO_ANSWER in rag_answer:
        groundedness = {
            "score": 0,
            "verdict": "El contexto recuperado no contiene información relevante para responder la pregunta.",
            "unsupported_claims": "N/A",
        }
        relevance = {
            "score": 0,
            "verdict": "La pregunta no pudo responderse: no hay información disponible en la base de conocimiento.",
            "missing_aspects": req.question,
        }
    else:
        groundedness = judge_groundedness(req.question, rag_answer, chunks)
        relevance = judge_relevance(req.question, rag_answer)

    get_client().score_current_trace(
        name="groundedness",
        value=groundedness["score"],
        comment=groundedness.get("verdict"),
    )
    get_client().score_current_trace(
        name="relevance",
        value=relevance["score"],
        comment=relevance.get("verdict"),
    )

    get_client().update_current_trace(
        output=rag_answer,
        metadata={"sources": source_names},
    )

    return EvalResponse(
        question=req.question,
        rag_answer=rag_answer,
        sources=source_names,
        groundedness=groundedness,
        relevance=relevance,
    )
