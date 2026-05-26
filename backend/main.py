from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langfuse.decorators import langfuse_context
from config import settings
from routers import chat, eval

langfuse_context.configure(
    public_key=settings.langfuse_public_key,
    secret_key=settings.langfuse_secret_key,
    host=settings.langfuse_host,
    debug=False,
)

app = FastAPI(title="Nyvia Brain API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(eval.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "nyvia-brain"}


@app.on_event("shutdown")
def shutdown():
    langfuse_context.flush()
