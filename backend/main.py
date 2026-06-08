from dotenv import load_dotenv
load_dotenv()

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langfuse import get_client
from config import settings
from routers import chat, eval

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nyvia Brain API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error in %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"Error interno: {type(exc).__name__}: {exc}"})


app.include_router(chat.router)
app.include_router(eval.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nyvia-brain"}


@app.get("/debug")
def debug():
    """Prueba cada componente sin Langfuse. Úsalo para diagnosticar 500s."""
    results = {}

    # 1. Env vars presentes
    results["env"] = {
        "VOYAGE_API_KEY": bool(settings.voyage_api_key),
        "ANTHROPIC_API_KEY": bool(settings.anthropic_api_key),
        "QDRANT_URL": bool(settings.qdrant_url),
        "QDRANT_API_KEY": bool(settings.qdrant_api_key),
        "QDRANT_COLLECTION": settings.qdrant_collection,
        "LANGFUSE_HOST": settings.langfuse_host,
        "LANGFUSE_PUBLIC_KEY": bool(settings.langfuse_public_key),
        "LANGFUSE_SECRET_KEY": bool(settings.langfuse_secret_key),
    }

    # 2. Qdrant — listar colecciones
    try:
        from qdrant_client import QdrantClient
        qc = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None, timeout=10)
        cols = [c.name for c in qc.get_collections().collections]
        results["qdrant"] = {"ok": True, "collections": cols}
    except Exception as e:
        results["qdrant"] = {"ok": False, "error": str(e)}

    # 3. VoyageAI — embed corto
    try:
        import voyageai
        vc = voyageai.Client(api_key=settings.voyage_api_key)
        vec = vc.embed(["test"], model=settings.embedding_model, input_type="query").embeddings[0]
        results["voyage"] = {"ok": True, "dim": len(vec)}
    except Exception as e:
        results["voyage"] = {"ok": False, "error": str(e)}

    # 4. Anthropic — mensaje mínimo
    try:
        import anthropic
        ac = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        r = ac.messages.create(
            model=settings.anthropic_model,
            max_tokens=10,
            messages=[{"role": "user", "content": "di 'ok'"}],
        )
        results["anthropic"] = {"ok": True, "reply": r.content[0].text}
    except Exception as e:
        results["anthropic"] = {"ok": False, "error": str(e)}

    return results


@app.on_event("shutdown")
def shutdown():
    get_client().flush()
