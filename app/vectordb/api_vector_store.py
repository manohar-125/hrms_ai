import json
from app.embeddings.embedding_model import EmbeddingModel
from app.vectordb.chroma_client import get_chroma_client

COLLECTION_NAME = "api_tools"


class APIVectorStore:

    def __init__(self):

        self.embedder = EmbeddingModel()

        self.collection = get_chroma_client().get_or_create_collection(
            name=COLLECTION_NAME
        )

    def index_tools(self, registry_path="app/tools/api_registry.json"):

        with open(registry_path) as f:
            registry = json.load(f)

        docs = []
        ids = []

        for tool_name, tool in registry.items():

            text = f"""
            tool_name: {tool_name}
            description: {tool.get('description','')}
            endpoint: {tool.get('endpoint')}
            domain: {tool.get('domain')}
            """

            docs.append(text)
            ids.append(tool_name)

        embeddings = self.embedder.embed_documents(docs)

        self.collection.upsert(
            documents=docs,
            embeddings=embeddings,
            ids=ids
        )

    def search_tools(self, query, k=5):
        """
        Legacy method: returns only tool names.
        Preserved for backward compatibility.
        """
        embedding = self.embedder.embed_text(query)

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k
        )

        return results["ids"][0]

    def search_tools_with_scores(self, query, k=5):
        """
        Enhanced method: returns tool names with similarity scores.
        Useful for ranking and improved tool selection.
        """
        embedding = self.embedder.embed_text(query)

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["distances"]
        )

        tool_names = results["ids"][0]
        distances = results["distances"][0]

        # Convert cosine distance to similarity score
        # similarity = 1 - distance
        scores = [1 - distance for distance in distances]

        # Return list of tuples: (tool_name, similarity_score)
        return list(zip(tool_names, scores))