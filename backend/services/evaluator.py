import json
import anthropic
from langfuse import observe, get_client
from config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

_GROUNDEDNESS_SYSTEM = """Eres un evaluador experto de sistemas RAG.
Evalúa si la respuesta generada está FUNDAMENTADA en el contexto recuperado.

Groundedness mide si cada afirmación de la respuesta puede respaldarse directamente
con el contexto provisto. Una respuesta con score alto no incluye información que no
esté en el contexto.

Devuelve ÚNICAMENTE un JSON con esta estructura:
{
  "score": <entero 0-100, donde 100 = completamente fundamentada en el contexto>,
  "verdict": "<una oración con el veredicto>",
  "unsupported_claims": "<afirmaciones en la respuesta que NO están en el contexto, o 'Ninguna' si todas están soportadas>"
}"""

_RELEVANCE_SYSTEM = """Eres un evaluador experto de sistemas RAG.
Evalúa si la respuesta generada es RELEVANTE a la pregunta formulada.

Relevance mide qué tan bien la respuesta aborda directamente la pregunta del usuario,
sin desviarse ni incluir información innecesaria.

Devuelve ÚNICAMENTE un JSON con esta estructura:
{
  "score": <entero 0-100, donde 100 = respuesta perfectamente relevante a la pregunta>,
  "verdict": "<una oración con el veredicto>",
  "missing_aspects": "<aspectos de la pregunta que la respuesta no aborda, o 'Ninguno' si cubre todo>"
}"""


@observe(as_type="generation")
def _judge_call(system: str, user_msg: str, judge_name: str = "judge") -> dict:
    get_client().update_current_generation(
        name=f"judge-{judge_name}",
        model=settings.judge_model,
        input=[{"role": "user", "content": user_msg}],
    )

    resp = _client.messages.create(
        model=settings.judge_model,
        max_tokens=512,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )

    result = json.loads(resp.content[0].text)

    get_client().update_current_generation(
        output=result,
        usage={
            "input": resp.usage.input_tokens,
            "output": resp.usage.output_tokens,
            "total": resp.usage.input_tokens + resp.usage.output_tokens,
        },
    )

    return result


def judge_groundedness(question: str, rag_answer: str, context_chunks: list[dict]) -> dict:
    context_text = "\n\n---\n\n".join(
        f"[Fuente: {c.get('source', 'desconocido')}]\n{c.get('text', '')}"
        for c in context_chunks
    )
    user_msg = f"""Pregunta: {question}

--- Contexto recuperado ---
{context_text}

--- Respuesta generada por el RAG ---
{rag_answer}"""
    return _judge_call(_GROUNDEDNESS_SYSTEM, user_msg, judge_name="groundedness")


def judge_relevance(question: str, rag_answer: str) -> dict:
    user_msg = f"""Pregunta: {question}

--- Respuesta generada por el RAG ---
{rag_answer}"""
    return _judge_call(_RELEVANCE_SYSTEM, user_msg, judge_name="relevance")
