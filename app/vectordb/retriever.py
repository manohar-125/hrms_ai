from app.vectordb.chroma_client import get_hrms_collection
from app.embeddings.embedding_model import get_embedding

collection = get_hrms_collection()


def retrieve_documents(query: str, top_k: int = 3, where: dict | None = None, return_metadata: bool = False):
    """
    Retrieve documents from ChromaDB.
    
    Args:
        query: Search query text
        top_k: Number of results to return
        where: Optional metadata filter dict for ChromaDB
        return_metadata: If True, returns (documents, metadatas); if False, returns documents only
    
    Returns:
        If return_metadata=False: list of document strings
        If return_metadata=True: tuple of (list of documents, list of metadata dicts)
    """
    query_embedding = get_embedding(query)

    query_params = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
    }
    if where:
        query_params["where"] = where

    results = collection.query(**query_params)

    documents = results.get("documents", [])
    docs = documents[0] if documents else []
    
    if return_metadata:
        metadatas = results.get("metadatas", [])
        metas = metadatas[0] if metadatas else []
        return docs, metas
    
    return docs