from sentence_transformers import SentenceTransformer

# Load model once (singleton style)
_model = SentenceTransformer("BAAI/bge-small-en")


def get_embedding(text: str):
    """
    Returns embedding vector for a single text.
    Used by retriever.py
    """
    return _model.encode(text).tolist()


class EmbeddingModel:
    """
    Wrapper class used by policy_service.py
    """

    def embed_text(self, text: str):
        return _model.encode(text).tolist()

    def embed_documents(self, docs: list[str]):
        return _model.encode(docs).tolist()