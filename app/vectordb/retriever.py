from app.vectordb.chroma_client import collection
from app.embeddings.embedding_model import get_embedding


def retrieve_documents(query: str, top_k: int = 3):

    query_embedding = get_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results["documents"][0]