import chromadb
from chromadb.utils import embedding_functions

from app.config import settings


# BGE embedding function
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=settings.EMBED_MODEL
)


# Persistent Chroma client
_client = chromadb.PersistentClient(
    path=settings.CHROMA_PATH
)


def get_chroma_client():
    return _client


def get_hrms_collection():
    return _client.get_or_create_collection(
        name="hrms_documents",
        embedding_function=embedding_function
    )