# RAG Pipeline

## Chunking Strategy
- Character-based chunking
- Overlap to prevent sentence truncation
- Low-value chunk filtering (TOC, references, boilerplate)

## Retrieval Strategy
- Query embedding
- Vector similarity search
- Deduplication
- Dynamic context sizing

## Prompt Grounding Rules
- Answer only using retrieved context
- Explicit citations per paragraph
- Ask clarifying questions when context is missing