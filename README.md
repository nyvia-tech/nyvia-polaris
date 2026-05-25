# Nyvia Polaris — Base de conocimiento interna

Sistema RAG (Retrieval-Augmented Generation) que permite al equipo de Nyvia consultar conocimiento interno en lenguaje natural. Incluye chat con citas de fuentes y panel de evaluación automática de calidad.

---

## Arquitectura

```
Pregunta del usuario
        │
        ▼
  [Frontend Next.js]
        │  POST /api/backend/chat/
        ▼
  [Backend FastAPI]
        │
        ├─► embed_query()  ──►  OpenAI text-embedding-3-small
        │
        ├─► search()  ──────►  Qdrant (vector DB, local o cloud)
        │         recupera top-K chunks relevantes
        │
        └─► ask()  ─────────►  OpenAI gpt-4o
                    genera respuesta usando los chunks como contexto
```

**Stack:**

| Capa | Tecnología |
|---|---|
| LLM + embeddings | OpenAI (`gpt-4o`, `text-embedding-3-small`) |
| Vector DB | Qdrant (Docker local o Qdrant Cloud) |
| Backend API | FastAPI + Uvicorn |
| Frontend | Next.js 14 + Tailwind CSS + TypeScript |
| Observabilidad | Langfuse |
| Auth (futuro) | Supabase |

---

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — para Qdrant local
- [Python 3.11+](https://www.python.org/downloads/) — marcar "Add Python to PATH" en el instalador
- [Node.js 20 LTS](https://nodejs.org/)
- Cuentas con claves de API en: [OpenAI](https://platform.openai.com/) y [Langfuse](https://cloud.langfuse.com/)

---

## Configuración inicial (una sola vez)

### 1. Variables de entorno

Crea el archivo `backend/.env` con el siguiente contenido:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Qdrant (dejar vacío para usar local con Docker)
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_COLLECTION=nyvia_brain

# Modelos (valores por defecto)
OPENAI_MODEL=gpt-4o
JUDGE_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536

# Langfuse (observabilidad)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Supabase (opcional, para auth futura)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
```

### 2. Levantar Qdrant (base de vectores)

```bash
docker-compose up -d
```

Verificar que está corriendo: http://localhost:6333/dashboard

### 3. Instalar dependencias del backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 4. Instalar dependencias del frontend

```bash
cd frontend
npm install
```

---

## Arranque diario

Abrir **tres terminales** en la raíz del proyecto:

**Terminal 1 — Qdrant:**
```bash
docker-compose up -d
```

**Terminal 2 — Backend:**
```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload
```
Backend disponible en: http://localhost:8000  
Documentación de la API: http://localhost:8000/docs

**Terminal 3 — Frontend:**
```bash
cd frontend
npm run dev
```
App disponible en: http://localhost:3000

---

## Indexar documentos

Los documentos viven en la carpeta `/docs` como archivos Markdown. Para indexarlos en Qdrant:

```bash
cd backend
venv\Scripts\activate
python ../scripts/index_documents.py
```

El script **elimina y recrea** la colección completa en cada ejecución (full re-index). Al finalizar imprime el total de chunks indexados.

### Formato de los documentos

Cada `.md` puede incluir un bloque de frontmatter con metadatos:

```markdown
---
source: nombre_del_destilado
client: nombre_cliente
dimension: estrategia
date: 2026-05-01
nda_level: bajo
---

Contenido del documento...
```

Los campos `source`, `client`, `dimension`, `date` y `nda_level` quedan almacenados como payload en Qdrant y son filtrables desde la API.

### Parámetros de chunking

| Parámetro | Valor |
|---|---|
| Tamaño de chunk | 1200 caracteres |
| Overlap | 200 caracteres |
| Mínimo para indexar | 50 caracteres |

---

## Estructura del proyecto

```
KM Polaris/
├── docker-compose.yml          ← Qdrant local (puerto 6333)
├── README.md
├── ARRANQUE.md                 ← Guía de arranque resumida
│
├── backend/
│   ├── main.py                 ← FastAPI entry point, CORS, Langfuse
│   ├── config.py               ← Variables de entorno (pydantic-settings)
│   ├── requirements.txt
│   ├── .env                    ← Credenciales (NO subir a git)
│   ├── routers/
│   │   ├── chat.py             ← POST /chat/
│   │   └── eval.py             ← POST /eval/
│   └── services/
│       ├── embeddings.py       ← OpenAI text-embedding-3-small
│       ├── vector_store.py     ← Qdrant: upsert, search, delete
│       ├── llm.py              ← OpenAI gpt-4o, system prompt de Nyvia Brain
│       └── evaluator.py        ← LLM-as-Judge: groundedness y relevance
│
├── frontend/
│   └── app/
│       ├── page.tsx            ← Layout con tabs Chat / Evaluación
│       ├── layout.tsx          ← Root layout, metadata
│       └── components/
│           ├── Chat.tsx        ← Interfaz de chat con citas de fuentes
│           └── Eval.tsx        ← Panel de evaluación con score bars
│
├── scripts/
│   └── index_documents.py     ← Indexador batch de archivos Markdown
│
└── docs/
    └── *.md                   ← Documentos de conocimiento (fuente de verdad)
```

---

## API

### `POST /chat/`

Responde una pregunta usando RAG.

**Request:**
```json
{
  "question": "¿Cuáles son los servicios de Nyvia?",
  "top_k": 8,
  "filters": { "client": "nombre_cliente" }
}
```

**Response:**
```json
{
  "answer": "Nyvia ofrece... [Fuente: DST-202605-001]",
  "sources": [
    {
      "source": "DST-202605-001",
      "score": 0.9124,
      "text": "Fragmento del chunk (primeros 300 caracteres)..."
    }
  ]
}
```

### `POST /eval/`

Evalúa la calidad de una respuesta RAG con LLM-as-Judge.

**Request:**
```json
{
  "question": "¿Cuáles son los pilares de la metodología?",
  "top_k": 5
}
```

**Response:**
```json
{
  "question": "...",
  "rag_answer": "...",
  "sources": ["DST-202605-003", "DST-202605-007"],
  "groundedness": {
    "score": 85,
    "verdict": "La respuesta está bien fundamentada en el contexto.",
    "unsupported_claims": "Ninguna"
  },
  "relevance": {
    "score": 90,
    "verdict": "La respuesta aborda directamente la pregunta.",
    "missing_aspects": "Ninguno"
  }
}
```

### `GET /health`

```json
{ "status": "ok", "service": "nyvia-brain" }
```

---

## Observabilidad — Langfuse

Cada request a `/chat/` y `/eval/` genera una traza en Langfuse con:

- Tokens consumidos (input / output / total)
- Chunks recuperados de Qdrant con sus scores
- Scores de groundedness y relevance (en `/eval/`)
- Tiempo de cada llamada al LLM

Dashboard: https://cloud.langfuse.com

---

## Filtros por metadata

El endpoint `/chat/` acepta el campo `filters` para acotar la búsqueda a documentos específicos:

```json
{ "question": "...", "filters": { "client": "acme", "dimension": "estrategia" } }
```

Campos filtrables: `source`, `client`, `dimension`, `nda_level`.

---

## Notas de producción

- **Qdrant Cloud:** definir `QDRANT_URL` y `QDRANT_API_KEY` en `.env`. El código detecta automáticamente si debe usar local o cloud.
- **CORS:** actualmente abierto (`allow_origins=["*"]`). Restringir al dominio de producción antes de exponer públicamente.
- **Re-indexar:** cualquier cambio en `/docs` requiere correr manualmente `scripts/index_documents.py`. No hay sincronización automática.
- **El archivo `.env` no debe subirse a git.** Asegurarse de que está en `.gitignore`.
