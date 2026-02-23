import os
from dotenv import load_dotenv

from app.rag.supabase_rest import insert_document, insert_chunks, match_chunks
from app.rag.embeddings_gemini import embed_documents, embed_query

def main():
    load_dotenv()

    test_text = "Retrieval-Augmented Generation (RAG) improves factual grounding by retrieving relevant context from indexed documents."
    doc_emb = embed_documents([test_text])[0]
    print("Document embedding length:", len(doc_emb))

    doc_id = insert_document("validation_doc")
    insert_chunks([{
        "document_id": doc_id,
        "chunk_index": 0,
        "content": test_text,
        "metadata": {"source": "validate_rest"},
        "embedding": doc_emb
    }])
    print("Inserted chunk into Supabase ✅")

    q_emb = embed_query("What is retrieval-augmented generation?")
    print("Query embedding length:", len(q_emb))

    results = match_chunks(q_emb, match_count=5, filter_document_id=None)
    print("RPC returned rows:", len(results))
    if results:
        top = results[0]
        print("Top similarity:", top.get("similarity"))
        print("Top content preview:", top.get("content", "")[:120], "...")
        print("Validation successful ✅")
    else:
        print("No results returned ❌ Check match_chunks function and indexing.")

if __name__ == "__main__":
    main()