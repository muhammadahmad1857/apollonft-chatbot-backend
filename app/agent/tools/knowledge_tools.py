from app.rag import embedder, qdrant


async def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant context.

    Args:
        query: The search query to look up in the knowledge base.

    Returns:
        Relevant text snippets from the knowledge base joined by newlines.
    """
    vector = await embedder.embed(query)
    results = await qdrant.search(vector)
    if not results:
        return "No relevant information found in the knowledge base."
    return "\n\n".join(results)
