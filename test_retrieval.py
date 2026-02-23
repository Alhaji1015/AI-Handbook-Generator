from app.rag.embeddings_gemini import embed_query
from app.rag.supabase_rest import match_chunks

emb = embed_query("What is the thesis about?")
rows = match_chunks(emb, match_count=5, filter_document_ids=None)

print(rows[:2])