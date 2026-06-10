# Nyvia Polaris 

**Sistema de recuperación de conocimiento (RAG) de Nyvia** — un asistente conversacional que responde preguntas sobre el conocimiento interno de la empresa, citando documentos reales, con observabilidad y evaluación automática integradas (LLMOps).

Backend: `nyvia-brain` (FastAPI) · Frontend: Lovable (React) · Vectores: Qdrant Cloud · LLM: Claude (Anthropic) · Embeddings: Voyage AI · Observabilidad: Langfuse

---

## Tabla de contenidos

1. [¿Qué es Nyvia Polaris?](#1-qué-es-nyvia-polaris)  
2. [Guía rápida para usuarios (no técnicos)](#2-guía-rápida-para-usuarios-no-técnicos)  
3. [Arquitectura](#3-arquitectura)  
4. [Stack tecnológico](#4-stack-tecnológico)  
5. [Estructura del repositorio](#5-estructura-del-repositorio)  
6. [Replicación paso a paso](#6-replicación-paso-a-paso)  
   - [6.1 Prerrequisitos y cuentas](#61-prerrequisitos-y-cuentas)  
   - [6.2 Clonar y preparar el entorno local](#62-clonar-y-preparar-el-entorno-local)  
   - [6.3 Variables de entorno](#63-variables-de-entorno)  
   - [6.4 Crear la colección en Qdrant](#64-crear-la-colección-en-qdrant)  
   - [6.5 Preparar documentos: formato de destilados](#65-preparar-documentos-formato-de-destilados)  
   - [6.6 Ingesta de documentos](#66-ingesta-de-documentos)  
   - [6.7 Levantar el backend y verificarlo](#67-levantar-el-backend-y-verificarlo)  
   - [6.8 Frontend en Lovable](#68-frontend-en-lovable)  
   - [6.9 Despliegue en Railway](#69-despliegue-en-railway)  
7. [Costos, límites de gasto y administración de cuentas](#7-costos-límites-de-gasto-y-administración-de-cuentas)  
8. [Observabilidad con Langfuse](#8-observabilidad-con-langfuse)  
9. [Evaluación automática (LLM-as-a-Judge)](#9-evaluación-automática-llm-as-a-judge)  
10. [Pruebas desde el punto de vista del usuario (UAT)](#10-pruebas-desde-el-punto-de-vista-del-usuario-uat)  
11. [Troubleshooting](#11-troubleshooting)  
12. [Mantenimiento, pendientes y roadmap](#12-mantenimiento-pendientes-y-roadmap)  
13. [Apéndice: desarrollo asistido con Claude Code](#13-apéndice-desarrollo-asistido-con-claude-code)

---

## 1\. ¿Qué es Nyvia Polaris?

Nyvia Polaris es un sistema **RAG (Retrieval-Augmented Generation)**: en lugar de que el modelo de lenguaje "invente" respuestas desde su memoria, primero **busca** los fragmentos más relevantes del conocimiento interno de Nyvia en una base de datos vectorial, y luego **genera** la respuesta usando exclusivamente esos fragmentos como contexto.

Esto resuelve tres problemas típicos de usar un chatbot genérico en una empresa:

1. **Conocimiento propio.** El modelo responde con información de Nyvia (cultura, playbooks, procesos, proyectos), no con generalidades de internet.  
2. **Trazabilidad.** Cada respuesta puede rastrearse: qué se preguntó, qué fragmentos se recuperaron, qué respondió el modelo y cuánto costó (vía Langfuse).  
3. **Calidad medible.** Un segundo modelo evalúa automáticamente cada respuesta (¿está fundamentada en los documentos? ¿es relevante a la pregunta?), lo que permite detectar degradación con el tiempo.

El backend se llama internamente **`nyvia-brain`** y expone una API REST que consume el frontend construido en Lovable. Polaris funciona también como componente dentro de la plataforma **Nyvia OS**.

---

## 2\. Guía rápida para usuarios (no técnicos)

Si solo quieres **usar** Polaris (no instalarlo), esto es lo que necesitas saber:

**Cómo acceder.** Entra a la URL del frontend de Polaris ([https://nyvia-knowledge-hive.lovable.app](https://nyvia-knowledge-hive.lovable.app)) e **inicia sesión con tu cuenta**. Si no tienes cuenta, solicita el alta al equipo técnico ([tech@nyvia.mx](mailto:tech@nyvia.mx)). No necesitas instalar nada: funciona en el navegador.

**Cómo preguntar.** Escribe preguntas en lenguaje natural, como se las harías a un colega:

- "¿Cómo define Nyvia el accountability?"  
- "¿Cuál es el proceso de onboarding para un consultor nuevo?"  
- "Resume los valores de la cultura Nyvia."

**Buenas prácticas:**

- Sé específico. "¿Qué dice el playbook de ventas sobre el primer contacto con un cliente?" funciona mejor que "ventas".  
- Una pregunta a la vez da mejores resultados que tres preguntas en un mismo mensaje.  
- Si la respuesta no te convence, reformula la pregunta con otras palabras clave; la búsqueda es semántica y a veces un sinónimo recupera mejores documentos.

**Limitaciones importantes:**

- Polaris solo sabe lo que está en su base de conocimiento. Si un documento no fue ingestado, no puede responder sobre él (y un buen comportamiento del sistema es decir "no tengo información sobre eso" en lugar de inventar).  
  - Sin embargo, hasta cierto punto es buena práctica que el modelo alucine para que pueda dar respuestas más abiertas y que no esté tan limitado a la exactitud y precisión de las preguntas.  
- Las conversaciones quedan registradas con fines de observabilidad y mejora del sistema.

---

## 3\. Arquitectura

**Flujo de una pregunta (los tres spans que verás en Langfuse):**

1. **`embed-query`** — La pregunta del usuario se convierte en un vector numérico con el modelo de embeddings de Voyage AI.  
2. **`qdrant-search`** — Ese vector se compara contra los 800+ chunks indexados en Qdrant (distancia coseno) y se recuperan los *top-k* fragmentos más similares.  
3. **`llm-answer`** — Los fragmentos recuperados se inyectan como contexto en un prompt a Claude, que genera la respuesta final fundamentada en ellos.

Cada paso queda registrado como un *span* dentro de un *trace* de Langfuse, con latencia, tokens y costo.

**Autenticación y memoria conversacional.** El acceso al chat requiere iniciar sesión: la autenticación de usuarios está implementada con **Supabase Auth**. Además, el sistema tiene **memoria**: el historial de la conversación se persiste en Supabase y se incorpora como contexto en las siguientes preguntas, lo que permite hacer preguntas de seguimiento ("¿y eso cómo aplica en un proyecto con cliente?") sin repetir todo. 

---

## 4\. Stack tecnológico

| Capa | Tecnología | Rol |
| :---- | :---- | :---- |
| API | **FastAPI** \+ Uvicorn | Backend REST (Nyvia\_Polaris) |
| Embeddings | **Voyage AI** | Vectorización de preguntas y documentos |
| Base vectorial | **Qdrant Cloud** | Almacenamiento y búsqueda semántica (colección Nyvia\_Polaris, vectores de 1536 dim, distancia coseno) |
| LLM | **Claude (Anthropic)** | Generación de respuestas |
| Observabilidad | **Langfuse** (cuenta de empresa Nyvia) | Traces, spans, costos, scores de evaluación |
| Auth y memoria | **Supabase** | Autenticación de usuarios (Supabase Auth) y persistencia de la memoria conversacional  |
| Hosting backend | **Railway** | Despliegue del API |
| Frontend | **Lovable** (React) \+ GitHub | Chat UI, sincronizado con repo de GitHub |
| Config | **pydantic-settings** \+ `.env` | Manejo de variables de entorno |

Nota histórica: el proyecto inició con embeddings de OpenAI y migró a Voyage AI \+ Claude (ver ADR 0005 sobre proveedores de embeddings). Si encuentras referencias a `OPENAI_API_KEY` en archivos viejos, están obsoletas.

---

## 5\. Estructura del repositorio

nyvia-brain/

├── main.py              \# App FastAPI: CORS, manejo de errores, /health, /debug

├── config.py            \# Settings (pydantic-settings): lee variables de entorno

├── routers/

│   ├── chat.py          \# Endpoint del pipeline RAG: embed → search → answer

│   └── eval.py          \# Endpoint de evaluación LLM-as-a-Judge

├── requirements.txt     \# Dependencias Python

├── .env.example         \# Plantilla de variables de entorno (sin secretos)

└── README.md            \# Este documento

---

## 6\. Replicación paso a paso

Esta sección permite a cualquier desarrollador levantar una instancia de Polaris desde cero.

### 6.1 Prerrequisitos y cuentas

**Software local:**

- Python 3.11+  
- Git  
- (Opcional) `curl` o Postman para probar endpoints

**Cuentas y API keys** (todas tienen capa gratuita suficiente para empezar):

| Servicio | Para qué | Dónde obtener la key |
| :---- | :---- | :---- |
| Anthropic | Generación de respuestas con Claude | [https://console.anthropic.com](https://console.anthropic.com) → API Keys |
| Voyage AI | Embeddings | [https://dash.voyageai.com](https://dash.voyageai.com) → API Keys |
| Qdrant Cloud | Base vectorial | [https://cloud.qdrant.io](https://cloud.qdrant.io) → crear cluster gratuito → API Key |
| Langfuse | Observabilidad | [https://cloud.langfuse.com](https://cloud.langfuse.com) → Settings → API Keys (usar el proyecto de la **cuenta de empresa Nyvia**, no cuentas personales) |
| Supabase | Persistencia auxiliar | [https://supabase.com](https://supabase.com) → proyecto → Settings → API |
| Railway | Hosting del backend | [https://railway.app](https://railway.app) (conectar con GitHub) |
| Lovable | Frontend | [https://lovable.dev](https://lovable.dev) (conectar con GitHub) |

### 6.2 Clonar y preparar el entorno local

\# 1\. Clonar el repositorio

git clone https://github.com/nyvia-tech/nyvia-polaris.git

cd nyvia-brain

### 6.3 Variables de entorno

Crea un archivo `.env` en la raíz del proyecto. **Nunca commitees este archivo** (debe estar en `.gitignore`); lo que se commitea es `.env.example` con valores de muestra. **Puedes pasar temporalmente estas credenciales a Claude Code y luego eliminarlas.**

\# \=== LLM y Embeddings \===

ANTHROPIC\_API\_KEY=sk-ant-...            \# Key de Anthropic (Claude)

ANTHROPIC\_MODEL=claude-sonnet-4-20250514 \# Modelo de generación

VOYAGE\_API\_KEY=pa-...                   \# Key de Voyage AI

EMBEDDING\_MODEL=voyage-large-2          \# Modelo de embeddings (1536 dim) 

\# \=== Qdrant (base vectorial) \===

QDRANT\_URL=https://xxxx.aws.cloud.qdrant.io

QDRANT\_API\_KEY=eyJh...

QDRANT\_COLLECTION=Nyvia\_Polaris

\# \=== Langfuse (observabilidad) — cuenta de empresa \===

LANGFUSE\_HOST=https://cloud.langfuse.com

LANGFUSE\_PUBLIC\_KEY=pk-lf-...

LANGFUSE\_SECRET\_KEY=sk-lf-...

\# \=== Supabase \===

SUPABASE\_URL=https://xxxx.supabase.co

SUPABASE\_SERVICE\_KEY=eyJh...

**Explicación de cada variable:**

| Variable | Descripción |
| :---- | :---- |
| `ANTHROPIC_API_KEY` | Autentica las llamadas a Claude para generar respuestas. |
| `ANTHROPIC_MODEL` | Qué modelo de Claude usar. Cambiar aquí permite subir/bajar de modelo sin tocar código. |
| `VOYAGE_API_KEY` | Autentica las llamadas de embedding. |
| `EMBEDDING_MODEL` | Modelo de embeddings. ⚠️ **Crítico:** su dimensionalidad debe coincidir con la de la colección de Qdrant (1536). Si cambias de modelo de embeddings, debes recrear la colección y re-ingestar todo. |
| `QDRANT_URL` / `QDRANT_API_KEY` | Endpoint y key del cluster de Qdrant Cloud. |
| `QDRANT_COLLECTION` | Nombre de la colección de vectores (Nyvia\_Polaris). |
| `LANGFUSE_*` | Credenciales del proyecto de Langfuse **de la empresa** donde se registran traces y scores. |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | Acceso a Supabase. La service key es de privilegio alto: solo en backend, jamás en frontend. |

### 6.4 Crear la colección en Qdrant

La colección que usa Polaris tiene esta configuración exacta (extraída de la instancia real):

- **Nombre:** `Nyvia_Polaris`  
- **Tamaño de vector:** `1536`  
- **Distancia:** `Cosine`

Buscar el script para crearla en Claude o Claude Code.

### 6.5 Preparar documentos: formato de destilados

El conocimiento que entra a Polaris no son documentos crudos, sino **destilados de conocimiento**: archivos Markdown estructurados generados con la plantilla interna de Nyvia (apoyada en NotebookLM) y revisados por una persona.

Cada destilado lleva un bloque de **metadata obligatoria** al inicio:

\# METADATA OBLIGATORIA, NO MODIFICAR ESTRUCTURA

destilado\_id: "CUL-202605-001"

fecha\_creacion: "2026-05-01"

autor\_nyvia: "NotebookLM"

revisor\_nyvia: "Nombre del revisor"

version: "1.0"

\# Clasificación

tipo\_fuente: "valores"  \# cultura\_interna | onboarding | valores | playbook | ritual | comunicacion

nda\_level: "bajo"        \# bajo | medio | alto

publicable\_externo: false

contiene\_pii: false

restricciones\_uso: "Uso interno Nyvia"

\# Tags

tags:

  \- "cultura"

  \- "valores"

\---

\# Título del documento

Contenido del destilado…

**Convención de nombres de archivo:** `<PREFIJO>-<AAAAMM>-<NNN>.md`, por ejemplo `CUL-202604-001.md` (CUL \= cultura).

### 6.6 Ingesta de documentos

Cada documento se parte en **chunks** y cada chunk se guarda en Qdrant como un *point* con este payload (esquema real de la colección, 811 points actualmente):

| Campo | Tipo | Descripción | Ejemplo |
| :---- | :---- | :---- | :---- |
| `text` | str | El contenido del chunk (lo que se inyecta al prompt) | "El accountability en Nyvia…" |
| `source` | str | Archivo de origen | `CUL-202604-001.md` |
| `client` | str | A qué cliente/ámbito pertenece el conocimiento | `nyvia_interno` |
| `dimension` | str | Dimensión o categoría del conocimiento | `general` |
| `date` | str | Fecha asociada al documento (puede ir vacía) | `""` |
| `nda_level` | str (opcional) | Nivel de confidencialidad del chunk | `bajo` |

Estos campos permiten **filtrar la búsqueda** (por ejemplo, restringir a un cliente específico o excluir contenido con `nda_level: alto`).

 **Puntos clave de la ingesta:**

**En el caso del apartado 6, de la ingesta. La indexación se realiza automáticamente apoyado de Claude Code. Más aún, a través de un script.**

- `input_type="document"` al embeber documentos y `input_type="query"` al embeber preguntas — Voyage optimiza distinto cada caso.  
- IDs determinísticos (UUID v5 sobre `archivo-índice`) hacen que re-ingestar un documento actualizado **reemplace** sus chunks en lugar de duplicarlos.  
- Verifica el conteo en el dashboard de Qdrant Cloud después de ingestar.  
- **\*Para facilitar el proceso de ingesta e Indexación se recomienda usar Claude Code.**

### 6.7 Levantar el backend y verificarlo

Con el entorno instalado y el `.env` lleno, el siguiente paso es encender el servidor en tu máquina y comprobar que todas las piezas se hablan entre sí antes de pensar en desplegar nada.

**La vía recomendada: con Claude Code.** Como en este proyecto trabajamos con Claude Code, no necesitas memorizar comandos: abre Claude Code en la raíz del repo y pídele algo como *"levanta el backend en el puerto 8000 y verifica que health, debug y chat respondan bien"*. Claude Code ejecuta el servidor, le pega a cada endpoint, interpreta las respuestas y, si algo falla, te dice qué variable o servicio es el problema y cómo arreglarlo. Lo que sigue abajo es exactamente lo que él hace tras bambalinas — léelo para entender qué se está verificando y por qué.

**Encender el servidor.** El comando es:

bash  
uvicorn main:app \--reload \--port 8000

Esto arranca la API en `http://localhost:8000`. La bandera `--reload` hace que el servidor se reinicie solo cada vez que guardas un cambio en el código — útil en desarrollo, nunca en producción.

**La verificación va de lo simple a lo completo, en tres niveles.** La lógica es de embudo: primero confirmas que el servicio existe, luego que puede hablar con el mundo exterior, y al final que el pipeline completo funciona. Así, cuando algo falla, sabes en qué capa está el problema.

**Nivel 1 — ¿El servicio vive?** Es la prueba más básica: el endpoint `/health` solo confirma que FastAPI arrancó. No toca ningún servicio externo, así que si esto falla, el problema está en tu instalación local (dependencias, puerto ocupado), no en las keys ni en internet.

bash  
curl http://localhost:8000/health  
\# → {"status": "ok", "service": "nyvia-brain"}

**Nivel 2 — ¿Los servicios externos responden?** Aquí entra `/debug`, la herramienta de diagnóstico principal del proyecto. Este endpoint prueba **cada componente externo por separado**: revisa que las variables de entorno estén presentes, que Qdrant responda y liste sus colecciones, que Voyage AI pueda generar un embedding (y confirma su dimensión, que debe ser 1536), y que Claude conteste un mensaje mínimo.

bash  
curl http://localhost:8000/debug  
json  
{  
  "env":      { "VOYAGE\_API\_KEY": true, "ANTHROPIC\_API\_KEY": true, "QDRANT\_URL": true, "...": "..." },  
  "qdrant":   { "ok": true, "collections": \["Nyvia\_Polaris"\] },  
  "voyage":   { "ok": true, "dim": 1536 },  
  "anthropic":{ "ok": true, "reply": "ok" }  
}

La gracia de `/debug` es que aísla el problema por ti: si un componente marca `"ok": false`, su campo `error` te dice exactamente qué falló (una key inválida, una URL mal escrita, un cluster pausado) sin tener que bucear en logs. Es lo primero que hay que consultar ante cualquier error 500, en local o en producción.

**Nivel 3 — ¿El pipeline RAG completo funciona?** La prueba final es hacer una pregunta real. Esto recorre todo el flujo de la sección 3: embebe la pregunta, busca en Qdrant y genera la respuesta con Claude.

bash  
curl \-X POST http://localhost:8000/chat \\  
  \-H "Content-Type: application/json" \\  
  \-d '{"question": "¿Cómo define Nyvia el accountability?"}'

Si recibes una respuesta coherente y fundamentada en los documentos, el backend está listo para desplegarse (sección 6.9).

**Bonus:** FastAPI genera documentación interactiva automática en `http://localhost:8000/docs` (Swagger). Ahí puedes ver todos los endpoints, sus parámetros, y probarlos desde el navegador sin usar `curl`.

### 6.8 Frontend en Lovable

El frontend es una app de chat en React construida y editada en **Lovable**, sincronizada con un repositorio de GitHub. Lovable funciona como editor visual/asistido: cada cambio que haces ahí se commitea automáticamente al repo, y viceversa (puedes editar el código en GitHub o localmente y Lovable lo refleja).

**Cómo está conectada toda la herramienta (de punta a punta):**

Usuario → Frontend (Lovable, hospedado en \*.lovable.app)

            ├── Supabase Auth  → login / registro / sesión del usuario

            └── fetch al backend (Railway) → pipeline RAG → respuesta

                                    └── lee/escribe historial en Supabase (memoria)

**Para replicarlo:**

1. **Crear el proyecto.** En Lovable, crea un proyecto nuevo (o haz *remix* del proyecto existente de Polaris) y conéctalo a GitHub: *Settings → GitHub → Connect*. Esto crea/enlaza el repo del frontend bajo la organización de Nyvia en GitHub (no bajo cuentas personales — ver sección 7).  
2. **Conectar Supabase.** Lovable tiene integración nativa con Supabase (*Settings → Integrations → Supabase*). Conéctala al proyecto de Supabase de Polaris: esto habilita Supabase Auth en el frontend (pantallas de login/registro y manejo de sesión).  
3. **Variables de entorno del frontend** (*Settings → Environment Variables*):  
   - `VITE_API_URL` → URL del backend (en local `http://localhost:8000`, en producción la URL de Railway).   
   - `VITE_SUPABASE_URL` y `VITE_SUPABASE_ANON_KEY` → del dashboard de Supabase (*Settings → API*). **Importante:** en el frontend solo va la *anon key* (pública por diseño); la `SERVICE_KEY` jamás sale del backend.  
4. **Flujo de autenticación.** El usuario inicia sesión vía Supabase Auth; las rutas del chat solo son accesibles con sesión activa.   
5. **Publicar.** En Lovable, *Publish* genera la URL pública (`https://<proyecto>.lovable.app`). También puedes conectar un dominio propio.

**CORS:** en `main.py` el middleware de CORS está abierto (`allow_origins=["*"]`) para simplificar la integración con Lovable y Nyvia OS. Para producción se recomienda restringirlo a los dominios reales.

### 6.9 Despliegue en Railway

1. Entra a [https://railway.app](https://railway.app) → **New Project → Deploy from GitHub repo** → selecciona el repo del backend.  
2. Railway detecta Python automáticamente. Configura el **start command**:  
3. En la pestaña **Variables**, agrega todas las variables de la sección 6.3 (Railway no lee tu `.env`; se configuran en su dashboard).  
4. En **Settings → Networking → Generate Domain** obtienes la URL pública del API.  
5. Verifica: `https://<tu-app>.up.railway.app/health` y luego `/debug`.  
6. Actualiza `VITE_API_URL` en Lovable con esa URL.

Cada `git push` a la rama principal redespliega automáticamente.

---

## 7\. Costos, límites de gasto y administración de cuentas

### 7.1 Principio: todo bajo la cuenta de empresa

Todos los servicios de Polaris deben vivir bajo cuentas de la empresa ([**tech@nyvia.mx**](mailto:tech@nyvia.mx) / organización de Nyvia en GitHub), nunca bajo cuentas personales de empleados. Esto evita perder acceso o facturación cuando alguien deja el equipo.

### 7.2 Límites de gasto configurados

| Servicio | Cuenta registrada | Límite duro (hard limit) | Alerta / threshold | Notas |
| :---- | :---- | :---- | :---- | :---- |
| Anthropic (Claude API) | [tech@nyvia.mx](mailto:tech@nyvia.mx) | $30 USD | $25 USD | Configurado en console.anthropic.com → Billing |
| Voyage AI | [tech@nyvia.mx](mailto:tech@nyvia.mx) | — | $20 USD | Threshold de gasto en dash.voyageai.com |
| Railway | [tech@nyvia.mx](mailto:tech@nyvia.mx) | $30 USD | $25 USD (alerta por email) | Migrado desde cuenta personal de GitHub. Actualmente operando en el plan gratuito |
| Qdrant Cloud | [tech@nyvia.mx](mailto:tech@nyvia.mx)  | No disponible | No disponible | Qdrant **no ofrece spend limits ni alertas de presupuesto**, pero su modelo de cobro lo hace innecesario: cobra por la infraestructura asignada (vCPU, RAM, disco del cluster), no por uso. El costo mensual es fijo y predecible sin importar el volumen de queries |
| Langfuse | Cuenta de empresa Nyvia | — | — | Plan gratuito (Hobby); migrado desde cuenta personal |
| Supabase |  | — | — | Plan gratuito |

**Regla operativa:** si llega una alerta de threshold a [tech@nyvia.mx](mailto:tech@nyvia.mx), revisar en Langfuse qué está generando el consumo (volumen de preguntas, prompts inusualmente largos) antes de subir el límite.

### 7.3 Convención de nombres y etiquetas

Para que los recursos sean identificables entre proyectos de la organización:

- **Proyectos en cada servicio** (Railway, Langfuse, Supabase, cluster de Qdrant): nombrarlos con el patrón `nyvia-<proyecto>`, p. ej. `nyvia-polaris` / `nyvia-brain`.  
- **Etiquetas/tags** donde el servicio lo permita: etiquetar con el nombre del proyecto (`polaris`) y la organización (`nyvia`), para distinguir sus costos y recursos de otros proyectos de la empresa.  
- **Repositorios de GitHub**: bajo la organización de Nyvia, con nombres descriptivos (`nyvia-brain` para backend, `nyvia-polaris-frontend` para el frontend de Lovable). 

### 7.4 Traspaso de cuentas personales a la empresa

Estado actual y procedimiento para completar/repetir el traspaso:

**GitHub (repositorios):**

1. En el repo: *Settings → Danger Zone → Transfer ownership* → transferir a la organización de Nyvia.  
2. GitHub deja redirecciones automáticas, pero hay que **reconectar las integraciones** (Railway y Lovable pierden permisos al cambiar de dueño): volver a autorizar la GitHub App de cada servicio sobre la organización.  
3. Los colaboradores actualizan su remote: `git remote set-url origin git@github.com:<org-nyvia>/<repo>.git`

**Railway:** ✅ ya migrado a [tech@nyvia.mx](mailto:tech@nyvia.mx) (antes estaba en la cuenta personal de GitHub de un empleado). Si se repite en el futuro: crear el proyecto bajo la cuenta de empresa, reconectar el repo de GitHub, copiar las variables de entorno, generar el dominio y actualizar `VITE_API_URL` en Lovable.

**Langfuse:** ✅ ya migrado de cuenta personal a la cuenta de empresa. Las keys (`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`) en Railway deben ser las del proyecto de empresa.

**Checklist post-traspaso:** `/health` y `/debug` en producción responden OK → el frontend conecta → aparecen traces nuevos en el Langfuse de empresa → las alertas de billing llegan a [tech@nyvia.mx](mailto:tech@nyvia.mx).

---

## 8\. Observabilidad con Langfuse

Toda interacción con Polaris genera un **trace** en Langfuse (proyecto de la cuenta de empresa Nyvia) compuesto por tres spans:

| Span | Qué mide |
| :---- | :---- |
| `embed-query` | Latencia y costo de vectorizar la pregunta |
| `qdrant-search` | Latencia de la búsqueda vectorial \+ qué chunks se recuperaron y con qué score |
| `llm-answer` | Prompt completo enviado a Claude, respuesta, tokens y costo |

**Cómo usarlo:**

- Entra a [https://cloud.langfuse.com](https://cloud.langfuse.com) → proyecto de Polaris → **Traces**.  
- Cada trace muestra el árbol de spans con tiempos; al abrir `llm-answer` ves exactamente qué contexto recibió el modelo, lo cual es la herramienta \#1 para depurar respuestas malas ("¿la recuperación trajo los chunks equivocados o el modelo respondió mal con buenos chunks?").  
- El dashboard agrega costo por día, latencias p50/p95 y volumen de uso.

El cliente de Langfuse hace flush de eventos pendientes al apagar el servicio (`@app.on_event("shutdown")` en `main.py`), así que no se pierden trazas en redeploys.

---

## 9\. Evaluación automática (LLM-as-a-Judge)

El router `eval` implementa la evaluación automática: un LLM actúa como "juez" y califica las respuestas del sistema en dos dimensiones, registrando los scores en Langfuse:

| Métrica | Pregunta que responde |
| :---- | :---- |
| **Groundedness** (fundamentación) | ¿La respuesta se sostiene únicamente en los chunks recuperados, o el modelo alucinó información? |
| **Relevance** (relevancia) | ¿La respuesta realmente contesta la pregunta del usuario? |

**Flujo:** se toma (pregunta, contexto recuperado, respuesta), se envía al modelo juez con un prompt de evaluación, y el score resultante se adjunta al trace correspondiente en Langfuse. Esto permite:

- Monitorear la calidad del sistema en el tiempo (detección de *drift*).  
- Comparar configuraciones (p. ej., cambiar de modelo de embeddings y ver si groundedness mejora).  
- Identificar las preguntas peor respondidas para mejorar la base de conocimiento.

---

## 10\. Pruebas desde el punto de vista del usuario (UAT)

Antes de dar por bueno un despliegue (o después de cambios importantes), correr este checklist **como lo viviría un empleado**, no como desarrollador:

**Autenticación:**

- [ ] Puedo registrarme / me dieron de alta y el login funciona.  
- [ ] Con credenciales incorrectas, el sistema rechaza el acceso con un mensaje claro.  
- [ ] Al cerrar sesión, no puedo acceder al chat.  
- [ ] Mi sesión persiste al recargar la página.

**Calidad de respuestas:**

- [ ] Una pregunta con respuesta conocida (p. ej. "¿Cómo define Nyvia el accountability?") devuelve una respuesta correcta y consistente con el documento fuente.  
- [ ] Una pregunta **fuera de la base de conocimiento** (p. ej. "¿cuál es la capital de Mongolia?") recibe un "no tengo información sobre eso" en lugar de una respuesta inventada.  
- [ ] Una pregunta ambigua reformulada con sinónimos recupera resultados similares.  
- [ ] La memoria funciona: una pregunta de seguimiento ("¿y cómo se aplica eso en un proyecto?") usa el contexto de la conversación.

**Confidencialidad:**

- [ ] Contenido marcado con `nda_level: alto` no aparece en respuestas para usuarios que no deberían verlo. 

**Experiencia:**

- [ ] La respuesta llega en un tiempo razonable (referencia: \< 10 s).  
- [ ] La interfaz es usable desde el celular.  
- [ ] Si el backend está caído, el frontend muestra un error entendible (no una pantalla rota).

**Verificación cruzada (para quien ejecuta las pruebas):**

- [ ] Cada pregunta del checklist generó su trace en Langfuse con los tres spans.  
- [ ] Los scores de groundedness/relevance de las pruebas son razonables.

---

## 11\. Troubleshooting

| Síntoma | Causa probable | Solución |
| :---- | :---- | :---- |
| `/debug` → `qdrant.ok: false` | URL o API key de Qdrant incorrectas, o cluster pausado | Revisa `QDRANT_URL`/`QDRANT_API_KEY`; en el plan gratuito de Qdrant Cloud los clusters inactivos se suspenden — reactívalo desde el dashboard |
| `/debug` → `voyage.ok: false` | Key inválida o nombre de modelo mal escrito | Revisa `VOYAGE_API_KEY` y `EMBEDDING_MODEL` |
| `/debug` → `anthropic.ok: false` | Key inválida o sin crédito | Revisa `ANTHROPIC_API_KEY` y el saldo en console.anthropic.com |
| Respuestas vacías o "no encontré información" | La colección está vacía o el modelo de embeddings no coincide con el usado en la ingesta | Verifica el conteo de points en Qdrant; confirma que `EMBEDDING_MODEL` sea el mismo de la ingesta |
| Error de dimensión al hacer upsert/search | Cambiaste de modelo de embeddings sin recrear la colección | Recrea la colección con la dimensión correcta y re-ingesta todo |
| El frontend no conecta con el API (error CORS o network) | `VITE_API_URL` mal configurada o CORS restringido | Revisa la variable en Lovable; confirma el dominio en `allow_origins` |
| 500 en producción sin pista | — | Llama a `/debug` en la URL de producción: aísla el componente que falla |
| No aparecen traces en Langfuse | Keys de Langfuse incorrectas o de otro proyecto/cuenta | Confirma que las keys sean del proyecto de la **cuenta de empresa**, no de una cuenta personal |

---

## 12\. Mantenimiento, pendientes y roadmap

**Tareas recurrentes:**

- **Agregar conocimiento:** crear el destilado con la plantilla (sección 6.5) → revisión humana → correr la ingesta (sección 6.6) → validar con una pregunta de prueba.  
- **Revisar calidad:** monitorear scores de groundedness/relevance en Langfuse al menos semanalmente.  
- **Rotar keys:** las API keys deben rotarse si alguien sale del equipo o ante cualquier sospecha de exposición.  
- **Revisar costos:** confirmar mensualmente que el consumo está dentro de los límites de la sección 7.2.

**Pendientes identificados:**

- [ ] **2FA / MFA:** validar y activar autenticación de dos factores. Dos frentes: (a) para los usuarios de Polaris — Supabase Auth soporta MFA con TOTP de forma nativa (*Authentication → MFA* en el dashboard); (b) para las cuentas de servicio de [tech@nyvia.mx](mailto:tech@nyvia.mx) (GitHub, Railway, Qdrant, Anthropic, Voyage, Langfuse) — activar 2FA en cada una.  
- [ ] **Filtrado por `nda_level`:** confirmar que la búsqueda aplica filtros de confidencialidad según el usuario (ver sección 10).  
- [ ] **Restringir CORS** a los dominios reales de producción (ver sección 6.8).  
- [ ] **Validar el JWT de Supabase en el backend** para que `/chat` no sea accesible sin sesión (si la protección actual es solo de frontend).  
- [ ] **Google Analytics en Nyvia OS:** pendiente de la plataforma Nyvia OS (fuera del alcance de este repo); se documenta en el repositorio de Nyvia OS, pero se lista aquí porque Polaris vive dentro de esa plataforma y su tráfico se medirá ahí.

**Decisiones de arquitectura:** las decisiones importantes están documentadas como ADRs en el repo (p. ej., ADR 0005: selección de proveedor de embeddings, Voyage AI vs. OpenAI).

---

## 13\. Apéndice: desarrollo asistido con Claude Code

Este proyecto se desarrolló en gran parte con **Claude Code** (la herramienta de coding agéntico de Anthropic, desde la terminal o el IDE), y es la vía recomendada para mantenerlo o replicar un RAG similar. En la práctica, Claude Code ayudó/ayuda a:

- **Generar el esqueleto del proyecto:** estructura FastAPI, routers, configuración con pydantic-settings.  
- **Escribir y ajustar los scripts de ingesta y de creación de colecciones** (chunking, embeddings, upsert a Qdrant), iterando rápido cuando cambia el esquema del payload.  
- **Depurar el pipeline:** pegarle un trace de Langfuse o el output de `/debug` y pedirle el diagnóstico acota muchísimo el tiempo de debugging.  
- **Migraciones de proveedor:** el cambio de OpenAI a Voyage AI \+ Claude (ADR 0005\) implicó tocar config, ingesta y generación; con Claude Code se hizo como una sola tarea supervisada.  
- **Documentación:** mantener este README, los ADRs y los destilados sincronizados con el código.

Sugerencia de flujo para alguien nuevo: clona el repo, abre Claude Code en la raíz, y pídele "explícame la arquitectura de este proyecto y el flujo de una pregunta" — es la forma más rápida de hacer onboarding al código. 

---

*Mantenido por el equipo de Nyvia. Dudas técnicas: abrir un issue en este repositorio. Cuentas y accesos: [tech@nyvia.mx](mailto:tech@nyvia.mx)*  
