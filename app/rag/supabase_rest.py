import os
import requests

def _headers():
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def insert_document(doc_name: str) -> int:
    url = os.getenv("SUPABASE_URL").rstrip("/") + "/rest/v1/documents"
    r = requests.post(url, headers=_headers(), json={"doc_name": doc_name}, timeout=60)
    r.raise_for_status()
    return r.json()[0]["id"]

def insert_chunks(rows: list[dict]) -> None:
    url = os.getenv("SUPABASE_URL").rstrip("/") + "/rest/v1/chunks"
    r = requests.post(url, headers=_headers(), json=rows, timeout=120)
    r.raise_for_status()

def match_chunks(query_embedding: list[float], match_count: int = 8, filter_document_ids=None) -> list[dict]:
    url = os.getenv("SUPABASE_URL").rstrip("/") + "/rest/v1/rpc/match_chunks"

    # filter_document_ids should be either None or a list of ints
    payload = {
        "query_embedding": query_embedding,
        "match_count": match_count,
        "filter_document_ids": filter_document_ids,  # <-- list or None
    }

    r = requests.post(url, headers=_headers(), json=payload, timeout=60)
    r.raise_for_status()
    return r.json()
    