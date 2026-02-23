import os
from supabase import create_client, Client

def get_supabase() -> Client:
    url = os.getenv("https://dlixyqneiabdtrtdziyh.supabase.co")
    key = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRsaXh5cW5laWFiZHRydGR6aXloIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTU5NjUwNSwiZXhwIjoyMDg3MTcyNTA1fQ.re8NExABp8gCjU_AhJFTQeXAtDEdnPyz6ycUlySxyGI")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)

def insert_document(sb: Client, doc_name: str) -> int:
    res = sb.table("documents").insert({"doc_name": doc_name}).execute()
    return res.data[0]["id"]

def insert_chunks(sb: Client, document_id: int, chunks: list[dict], embeddings: list[list[float]]):
    rows = []
    for ch, emb in zip(chunks, embeddings):
        rows.append({
            "document_id": document_id,
            "chunk_index": ch["chunk_index"],
            "content": ch["content"],
            "metadata": ch.get("metadata", {}),
            "embedding": emb
        })
    # batch insert
    sb.table("chunks").insert(rows).execute()