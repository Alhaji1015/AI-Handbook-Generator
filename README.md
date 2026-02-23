\# 📚 AI Handbook Generator (PDF → RAG → Chat → 20k Word Handbook)



An AI-powered document intelligence platform that lets users upload PDFs, query them conversationally, and generate long-form structured handbooks grounded in the uploaded sources.



---



\## Overview



This project combines Retrieval-Augmented Generation (RAG), vector search, and Generative AI to turn unstructured PDF documents into an interactive knowledge system.



\*\*Key capabilities:\*\*



\- Upload and index PDFs

\- Semantic search across documents

\- NotebookLM-style scoped querying

\- Grounded AI chat responses with citations

\- Automatic handbook generation (20k+ words)

\- Multi-document filtering and retrieval



---



\## Features



\### Document Intelligence

\- PDF ingestion and text extraction

\- Chunking and embedding using Gemini embeddings

\- Vector storage in Supabase (pgvector)



\### Conversational AI

\- Context-aware question answering

\- Source citations per response

\- Document-level filtering



\### Handbook Generation

\- Automatic table of contents creation

\- Section-by-section grounded writing

\- Long-form structured output

\- Markdown export capability



---



\## Architecture



The system follows a Retrieval-Augmented Generation pipeline:



1\. PDF ingestion

2\. Text chunking

3\. Embedding generation

4\. Vector storage in Supabase

5\. Semantic retrieval

6\. LLM grounding and response generation



```

PDF → Extract Text → Chunk → Embed → Supabase Vector DB

&nbsp;                                            ↓

&nbsp;                                     Retrieve Context

&nbsp;                                            ↓

&nbsp;                                       Gemini LLM

&nbsp;                                            ↓

&nbsp;                             Chat Response or Handbook Output

```



---



\## Tech Stack



| Layer | Technology |

|-------|-----------|

| \*\*Frontend\*\* | Streamlit |

| \*\*LLM\*\* | Gemini (chat + embeddings) |

| \*\*Database\*\* | Supabase PostgreSQL + pgvector |

| \*\*PDF Parsing\*\* | pdfplumber |

| \*\*Core Libraries\*\* | google-genai, python-dotenv, requests |



---



\## Installation



\*\*Clone the repository:\*\*



```bash

git clone https://github.com/yourusername/ai-handbook-generator.git

cd ai-handbook-generator

```



\*\*Create a virtual environment:\*\*



```bash

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1   # Windows

source .venv/bin/activate       # macOS/Linux

```



\*\*Install dependencies:\*\*



```bash

pip install -r requirements.txt

```



---



\## Environment Variables



Create a `.env` file in the root directory:



```bash

GEMINI\_API\_KEY=your\_api\_key

SUPABASE\_URL=your\_supabase\_url

SUPABASE\_SERVICE\_ROLE\_KEY=your\_service\_role\_key

GEMINI\_CHAT\_MODEL=gemini-2.5-pro

GEMINI\_EMBED\_MODEL=gemini-embedding-001

GEMINI\_EMBED\_DIM=768

```



---



\## Run the App



```bash

streamlit run ui\_streamlit.py

```



---



\## Usage Workflow



1\. Upload one or more PDFs in the sidebar

2\. Click \*\*"Process \& Index"\*\* and wait for indexing to complete

3\. Ask questions about the documents in the chat

4\. Optionally select a document scope from the \*\*Search Scope\*\* dropdown

5\. Generate a full handbook by typing:



```

Generate a handbook on <topic>

```



---



\## License



MIT License



