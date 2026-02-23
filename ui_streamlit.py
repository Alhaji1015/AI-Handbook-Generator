import os
import tempfile
import streamlit as st
from dotenv import load_dotenv

from app.rag.pdf_extract import extract_text_from_pdf
from app.rag.chunking import chunk_text
from app.rag.embeddings_gemini import embed_documents, embed_query
from app.rag.supabase_rest import insert_document, insert_chunks, match_chunks

from app.llm.gemini_client import GeminiClient
from app.llm.prompts import SYSTEM_CHAT
from app.llm.longwriter import LongWriter, SourceChunk, format_sources

load_dotenv()

# ---------------------------
# Page Config & Custom CSS
# ---------------------------
st.set_page_config(
    page_title="Handbook Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# UI/UX Optimization: Custom CSS to remove whitespace and make UI compact
st.markdown("""
    <style>
        /* Reduce main container whitespace */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            max-width: 1200px;
        }
        /* Compact typography */
        h1 { margin-bottom: 0.5rem !important; padding-bottom: 0 !important; font-size: 2.2rem !important; }
        p { margin-bottom: 0.8rem !important; }
        /* Style chat bubbles to be more contained */
        [data-testid="stChatMessage"] {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: var(--secondary-background-color);
            margin-bottom: 0.5rem;
        }
        /* Compress dividers */
        hr { margin: 1.5em 0 !important; }
        /* Hide deploy button */
        .stDeployButton {display:none;}
    </style>
""", unsafe_allow_html=True)

llm = GeminiClient()
writer = LongWriter()

# ---------------------------
# Session state init
# ---------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "doc_map" not in st.session_state:
    st.session_state.doc_map = {}  # document_id -> doc_name
if "last_retrieval" not in st.session_state:
    st.session_state.last_retrieval = []
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs = []  # list of {"id": doc_id, "name": filename}
if "active_doc_id" not in st.session_state:
    st.session_state.active_doc_id = None


# ---------------------------
# Chunk quality filtering
# ---------------------------
def is_low_value(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 200:
        return True

    tl = t.lower()
    bad_signals = [
        "table of contents", "contents", "list of tables", "list of figures",
        "acknowledgement", "acknowledgment", "copyright",
        "all rights reserved", "bibliography", "references"
    ]
    if any(s in tl for s in bad_signals) and len(t) < 1200:
        return True

    if tl.count("...") >= 3:
        return True

    return False

# ---------------------------
# Sidebar: Upload, Scope & Debug
# ---------------------------
with st.sidebar:
    st.header("📂 Document Management")
    
    files = st.file_uploader(
        "Upload reference PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if st.button("Process & Index", use_container_width=True, type="primary") and files:
        for f in files:
            # UX: Using st.status for a clean, professional progress indicator
            with st.status(f"Processing {f.name}...", expanded=True) as status:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(f.read())
                    tmp_path = tmp.name

                try:
                    st.write("📄 Extracting text...")
                    text = extract_text_from_pdf(tmp_path)
                finally:
                    try: os.remove(tmp_path)
                    except Exception: pass

                if not text or not text.strip():
                    status.update(label=f"Failed: No text in {f.name}", state="error", expanded=False)
                    continue

                st.write("✂️ Chunking content...")
                raw_chunks = chunk_text(text, chunk_size=1400, overlap=250)
                chunks = [c for c in raw_chunks if c.get("content") and not is_low_value(c["content"])]
                contents = [c["content"] for c in chunks]

                if not contents:
                    status.update(label=f"Skipped: No useful chunks in {f.name}", state="warning", expanded=False)
                    continue

                st.write("🧠 Generating embeddings...")
                embs = embed_documents(contents)

                st.write("☁️ Uploading to database...")
                doc_id = insert_document(f.name)
                st.session_state.doc_map[doc_id] = f.name
                st.session_state.indexed_docs.append({"id": doc_id, "name": f.name})

                rows = [{
                    "document_id": doc_id,
                    "chunk_index": c.get("chunk_index", idx),
                    "content": c["content"],
                    "metadata": c.get("metadata", {}),
                    "embedding": embs[idx],
                } for idx, c in enumerate(chunks)]

                insert_chunks(rows)
                status.update(label=f"Indexed {f.name} ({len(chunks)} chunks) ✅", state="complete", expanded=False)

    st.divider()

    # ---------------------------
    # Search Scope Logic
    # ---------------------------
    st.header("🔍 Search Scope")

    # doc_map is {doc_id: doc_name}
    doc_options = [(doc_id, name) for doc_id, name in st.session_state.doc_map.items()]
    doc_options.sort(key=lambda x: x[1].lower())

    scope_mode = st.radio("Scope", ["All documents", "Selected documents"], index=0, label_visibility="collapsed")

    selected_doc_ids = None
    if scope_mode == "Selected documents":
        selected_names = st.multiselect(
            "Choose documents",
            options=[name for _, name in doc_options],
            default=[name for _, name in doc_options[:1]] if doc_options else [],
        )

        # map names back to ids
        name_to_id = {name: doc_id for doc_id, name in doc_options}
        selected_doc_ids = [name_to_id[n] for n in selected_names if n in name_to_id]

        if not selected_doc_ids:
            st.warning("Select at least one document, or switch back to All documents.")
            
    # Link the selected scoping to the session state for filtering
    # Now storing either None (All docs) or a List[str] of doc_ids
    st.session_state.active_doc_id = selected_doc_ids
    
    st.divider()
    
    # UX: Move debug info to sidebar expander to keep main chat area clean
    with st.expander("🛠️ Retrieved Context (Debug)"):
        rows = st.session_state.get("last_retrieval", [])
        if not rows:
            st.caption("No context retrieved yet.")
        else:
            for r in rows[:6]:
                doc_name = st.session_state.doc_map.get(r["document_id"], f"doc_{r['document_id']}")
                st.markdown(f"**{doc_name}** (Chunk {r['chunk_index']})")
                st.caption(f"Similarity: {r.get('similarity', 'n/a')}")
                st.text((r["content"] or "")[:300] + "...")
                st.divider()

# ---------------------------
# Main Layout: Header & State
# ---------------------------
st.title("📚 AI Handbook Generator")
st.caption("Upload PDFs → Ask Questions → Generate a 20k-word Markdown Handbook")

# UX: Empty State Onboarding
if not st.session_state.messages and not st.session_state.indexed_docs:
    st.info("👋 **Welcome!** Please upload a PDF in the sidebar to get started.")
elif not st.session_state.messages:
    st.success("✅ **Documents ready!** Ask a question below, or type `Generate a handbook on [topic]`.")

# ---------------------------
# Context builder (RAG)
# ---------------------------
def build_context(query: str, k: int = 16, filter_doc_id=None):
    q_emb = embed_query(query)

    if filter_doc_id is None:
        filter_doc_id = st.session_state.active_doc_id

    # Use plural to support lists
    results = match_chunks(q_emb, match_count=k, filter_document_ids=filter_doc_id)

    # Return early if retrieval fails or scope is completely empty
    if not results:
        return "", []

    unique = []
    seen = set()
    for r in results:
        key = (r["content"][:140] if r.get("content") else "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(r)

    results = unique[:k]
    st.session_state.last_retrieval = results

    src_chunks = []
    for r in results:
        doc_name = st.session_state.doc_map.get(r["document_id"], f"doc_{r['document_id']}")
        src_chunks.append(
            SourceChunk(
                doc_name=doc_name,
                chunk_index=r["chunk_index"],
                content=r["content"],
            )
        )

    # Dynamically scale limit_chars based on 'k' so we don't truncate large retrievals
    dynamic_limit = k * 1500
    return format_sources(src_chunks, limit_chars=dynamic_limit), results

def retrieve_sources_for_section(section_title: str, k: int = 18) -> str:
    ctx, _ = build_context(section_title, k=k, filter_doc_id=st.session_state.active_doc_id)
    return ctx

# ---------------------------
# Chat history render
# ---------------------------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------------------------
# Handle user input
# ---------------------------
user_input = st.chat_input("Ask a question, or say: Generate a handbook on <topic>")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    lower = user_input.lower().strip()
    active_doc = st.session_state.active_doc_id  # respect selected scope

    # 1. Handbook request
    if lower.startswith("generate a handbook on") or lower.startswith("create a handbook on"):
        topic = user_input.split("on", 1)[-1].strip()

        with st.chat_message("assistant"):
            with st.spinner(f"📝 Architecting handbook on '{topic}'. This may take several minutes..."):
                context, _ = build_context(topic, k=24, filter_doc_id=active_doc)

                if not context.strip():
                    st.warning("No context found for the selected scope. Try checking your documents.")
                    handbook_md = "I couldn't find sufficient context in the indexed PDFs for the selected scope."
                else:
                    handbook_md = writer.generate_handbook(
                        topic=topic,
                        initial_sources_text=context,
                        retrieve_sources_for_section=retrieve_sources_for_section,
                        target_words=20000,
                        section_token_budget=3500,
                        per_section_k=25,
                    )

            st.markdown(handbook_md)
            
            # Prevent word count and download button for empty handbook runs
            if context.strip():
                # ADDED: Live word counter
                st.info(f"📊 Current handbook length: {len(handbook_md.split()):,} words")
                
                st.download_button(
                    "📥 Download Handbook (Markdown)",
                    handbook_md,
                    file_name=f"handbook_{topic[:40].replace(' ', '_')}.md",
                    type="primary"
                )

        st.session_state.messages.append({"role": "assistant", "content": handbook_md})

    # 2. Normal Q&A
    else:
        with st.chat_message("assistant"):
            with st.spinner("Analyzing documents..."):
                if any(w in lower for w in ["Provide an overview", "Provide a summary", "summary", "abstract", "Provide the key findings", "conclusion"]):
                    retrieval_query = "abstract introduction methodology results discussion conclusion key findings"
                    # INCREASED 'k' for broad questions to 50
                    context, rows = build_context(retrieval_query, k=50, filter_doc_id=active_doc)
                else:
                    context, rows = build_context(user_input, k=16, filter_doc_id=active_doc)

                # Bypass LLM entirely if we have an empty context
                if not context.strip():
                    answer = "I couldn't find that in the indexed PDFs for the selected scope. Try rephrasing your question or select different documents."
                else:
                    grounded_rules = (
                        "Rules:\n"
                        "- Answer ONLY using the Context.\n"
                        "- If the answer is not in the Context, say: \"I couldn't find that in the indexed PDFs.\" "
                        "Then ask a clarifying question.\n"
                        "- Cite sources at the end of each paragraph like: (Doc: <n>, Chunk: <index>).\n"
                        "- Never claim the user did not provide a document if Context is present.\n"
                    )

                    prompt = f"{SYSTEM_CHAT}\n\nContext:\n{context}\n\nUser question: {user_input}\n\n{grounded_rules}"

                    messages = [
                        {"role": "system", "content": SYSTEM_CHAT},
                        {"role": "user", "content": prompt},
                    ]

                    answer = llm.chat(messages, temperature=0.2, max_tokens=1500)
            
            st.markdown(answer)
        
        st.session_state.messages.append({"role": "assistant", "content": answer})