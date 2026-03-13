from app.vectordb.chroma_client import collection
from app.embeddings.embedding_model import get_embedding


def add_document(doc_id: str, text: str):

    embedding = get_embedding(text)

    collection.add(
        ids=[doc_id],
        documents=[text],
        embeddings=[embedding]
    )