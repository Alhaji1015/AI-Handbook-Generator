from typing import List, Dict

def chunk_text(text: str, chunk_size: int = 1400, overlap: int = 250) -> List[Dict]:
    if not text:
        return []

    text = text.replace("\x00", "")
    text = " ".join(text.split())

    chunks: List[Dict] = []
    n = len(text)
    start = 0
    idx = 0

    chunk_size = max(300, int(chunk_size))
    overlap = max(0, min(int(overlap), chunk_size // 2))

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()

        if chunk and len(chunk) >= 200:
            chunks.append({"chunk_index": idx, "content": chunk})
            idx += 1

        if end >= n:
            break

        # FIX: guard is now inside the loop where it can actually prevent bad steps
        start = end - overlap
        if start < 0:
            start = 0

    return chunks