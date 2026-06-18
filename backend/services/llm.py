import re
import anthropic
from langfuse import observe, get_client
from config import settings


_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F1E0-\U0001F1FF"
    "\U00002500-\U00002BFF"
    "\U0000FE00-\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)


def _strip_emojis(text: str) -> str:
    return _EMOJI_RE.sub("", text)

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

NO_INFO_ANSWER = "No tengo esa información en la base de conocimiento de Nyvia."

SYSTEM_PROMPT = f"""Eres Nyvia Brain, el asistente de conocimiento interno de Nyvia, consultora de data y estrategia.

Responde basándote en los fragmentos de contexto proporcionados. Tu objetivo es dar la respuesta más útil posible a partir de ese material.

Reglas para responder:
- Si el contexto contiene información directa sobre la pregunta, úsala.
- Si el contexto habla de un caso específico que ilustra la pregunta (aunque sea de un cliente concreto), úsalo para responder e indica que el dato proviene de ese caso.
- Si la información es parcial, responde lo que está cubierto e indica qué aspectos no están en la base de conocimiento.
- Puedes sintetizar, inferir y conectar ideas entre fragmentos cuando tenga sentido.
- Cuando la pregunta pida enumerar elementos (fases, pasos, etapas, pilares, KPIs, etc.), incluye TODOS los que aparezcan en el contexto.
- Cita la fuente de las ideas principales con el formato [Fuente: nombre_archivo].
- Tono: experto, cercano y claro. Evita respuestas mecánicas o demasiado enumerativas.
- No uses emojis en ningún caso.
- Usa la frase "{NO_INFO_ANSWER}" SOLO si ninguno de los fragmentos tiene la menor relación con la pregunta.

Idioma: responde siempre en el mismo idioma de la pregunta."""


LOW_CONFIDENCE_NOTE = (
    "\n\nNOTA DE SISTEMA: Los fragmentos recuperados tienen relevancia moderada o baja. "
    "Aun así, extrae y sintetiza cualquier información relacionada — aunque sea indirectamente — "
    "para dar la respuesta más útil posible. Indica qué aspectos quedan sin cubrir si es necesario. "
    "Solo usa la frase de no-información si los fragmentos no guardan ninguna relación con la pregunta."
)


@observe(as_type="generation", name="llm-answer")
def ask(
    question: str,
    context_chunks: list[dict],
    low_confidence: bool = False,
    system_prompt_override: str | None = None,
    model_override: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    context_text = "\n\n---\n\n".join(
        f"[Fuente: {c.get('source', 'desconocido')}]\n{c.get('text', '')}"
        for c in context_chunks
    )

    base_prompt = system_prompt_override if system_prompt_override else SYSTEM_PROMPT
    system_content = base_prompt + (LOW_CONFIDENCE_NOTE if low_confidence else "")
    user_content = f"Contexto disponible:\n{context_text}\n\n---\n\nPregunta: {question}"
    model = model_override or settings.anthropic_model

    get_client().update_current_generation(
        model=model,
        input=[{"role": "user", "content": user_content}],
    )

    create_kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens if max_tokens is not None else 2048,
        cache_control={"type": "ephemeral"},
        system=system_content,
        messages=[{"role": "user", "content": user_content}],
    )
    if temperature is not None:
        create_kwargs["temperature"] = temperature

    response = _client.messages.create(**create_kwargs)

    answer = _strip_emojis(response.content[0].text)

    get_client().update_current_generation(
        output=answer,
        usage_details={
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        },
    )

    return answer
