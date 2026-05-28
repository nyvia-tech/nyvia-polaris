"""
Indexa archivos Markdown de /docs en Qdrant.
Uso:
    cd backend
    python ../scripts/index_documents.py
"""
import sys
import os
import re
import uuid
from pathlib import Path

# Permite importar desde /backend
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

from services.embeddings import embed_texts
from services.vector_store import upsert_chunks, delete_by_source, drop_and_recreate_collection

DOCS_DIR = Path(__file__).parent.parent / "docs"
CHUNK_SIZE = 1200  # caracteres por chunk
CHUNK_OVERLAP = 200


def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm = text[3:end].strip()
            for line in fm.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip('"')
            text = text[end + 3:].strip()
    elif "\n---\n" in text:
        # Formato destilado: metadata libre antes del primer "---"
        sep_idx = text.find("\n---\n")
        fm = text[:sep_idx]
        for line in fm.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("#") and not line.startswith("-"):
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').split("#")[0].strip()
        text = text[sep_idx + 5:].strip()
    return meta, text


def split_by_sections(text: str) -> list[str]:
    """Split on ## / ### headers to preserve semantic boundaries."""
    sections = re.split(r'\n(?=#{2,3}\s)', text)
    return [s.strip() for s in sections if len(s.strip()) > 50]


def split_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    sections = split_by_sections(text)
    # If no headers found, treat whole text as one section
    if not sections:
        sections = [text]

    chunks = []
    for section in sections:
        if len(section) <= size:
            chunks.append(section)
        else:
            start = 0
            while start < len(section):
                end = start + size
                chunks.append(section[start:end].strip())
                start += size - overlap
    return [c for c in chunks if len(c) > 50]


def index_file(filepath: Path) -> int:
    raw = filepath.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(raw)
    source = meta.get("source") or meta.get("destilado_id") or filepath.name
    client = meta.get("client", "nyvia_interno")
    dimension = meta.get("dimension") or meta.get("tipo_fuente") or "general"
    date = meta.get("date") or meta.get("fecha_creacion") or ""
    nda_level = meta.get("nda_level", "bajo")

    chunks_text = split_chunks(body)
    if not chunks_text:
        return 0

    vectors = embed_texts(chunks_text)

    chunks = [
        {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}::{i}")),
            "vector": vectors[i],
            "text": chunks_text[i],
            "source": source,
            "client": client,
            "dimension": dimension,
            "date": date,
            "nda_level": nda_level,
        }
        for i in range(len(chunks_text))
    ]

    upsert_chunks(chunks)
    return len(chunks)


def main():
    md_files = list(DOCS_DIR.glob("**/*.md"))
    if not md_files:
        print(f"No se encontraron archivos .md en {DOCS_DIR}")
        return

    print("Limpiando colección anterior...")
    drop_and_recreate_collection()

    total = 0
    for f in md_files:
        n = index_file(f)
        print(f"  {f.name}: {n} chunks indexados")
        total += n

    print(f"\nTotal: {total} chunks en Qdrant (colección '{os.getenv('QDRANT_COLLECTION', 'nyvia_brain')}')")


if __name__ == "__main__":
    main()
