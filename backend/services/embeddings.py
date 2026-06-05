import voyageai
from langfuse import observe, get_client
from config import settings

_client = voyageai.Client(api_key=settings.voyage_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    result = _client.embed(texts, model=settings.embedding_model, input_type="document")
    return result.embeddings


@observe(name="embed-query")
def embed_query(query: str) -> list[float]:
    get_client().update_current_span(
        input=query,
        metadata={"model": settings.embedding_model},
    )
    result = _client.embed([query], model=settings.embedding_model, input_type="query")
    return result.embeddings[0]
