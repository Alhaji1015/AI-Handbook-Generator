from typing import Optional
from .embeddings import embed_texts

def retrieve_top_k(sb, query: str, k: int = 8, document_id: Optional[int] = None) -> list[dict]:
    q_emb = embed_texts([query])[0]
    params = {
        "query_embedding": q_emb,
        "match_count": k,
        "filter_document_id": document_id
    }
    res = sb.rpc("match_chunks", params).execute()
    return res.data or []