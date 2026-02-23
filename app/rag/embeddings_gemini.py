import os
from google import genai
from google.genai import types

_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("Missing GEMINI_API_KEY in environment (.env)")
        _client = genai.Client(api_key=key)
    return _client


def embed_documents(texts, batch_size: int = 100):
    model = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    dim = int(os.getenv("GEMINI_EMBED_DIM", "768"))

    out = []
    client = _get_client()

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]

        resp = client.models.embed_content(
            model=model,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=dim,
            ),
        )

        out.extend([e.values for e in resp.embeddings])

    return out


def embed_query(text: str) -> list[float]:
    model = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    dim = int(os.getenv("GEMINI_EMBED_DIM", "768"))

    resp = _get_client().models.embed_content(
        model=model,
        contents=[text],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=dim,
        ),
    )

    return resp.embeddings[0].values