"""
CLI script to ingest text documents into Qdrant.

Usage:
    uv run python -m app.rag.ingest --file path/to/docs.txt
    uv run python -m app.rag.ingest --dir path/to/docs/
"""
import asyncio
import argparse
import uuid
from pathlib import Path
from qdrant_client.models import PointStruct
from app.rag import embedder, qdrant


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


async def ingest_file(file_path: Path) -> int:
    """Ingest a single text file. Returns number of chunks ingested."""
    text = file_path.read_text(encoding="utf-8")
    chunks = chunk_text(text)
    points = []
    for chunk in chunks:
        vector = await embedder.embed(chunk)
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={"text": chunk, "source": str(file_path)},
            )
        )
    await qdrant.ensure_collection()
    await qdrant.upsert(points)
    return len(points)


async def main(args: argparse.Namespace) -> None:
    files: list[Path] = []
    if args.file:
        files.append(Path(args.file))
    elif args.dir:
        files = list(Path(args.dir).rglob("*.txt"))

    total = 0
    for f in files:
        count = await ingest_file(f)
        print(f"Ingested {count} chunks from {f}")
        total += count
    print(f"Done. Total chunks: {total}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest documents into Qdrant.")
    parser.add_argument("--file", help="Path to a single text file")
    parser.add_argument("--dir", help="Path to a directory of .txt files")
    args = parser.parse_args()
    asyncio.run(main(args))
