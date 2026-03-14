from app.vectordb.retriever import retrieve_documents
from app.embeddings.embedding_model import EmbeddingModel
from app.embeddings.chunking import chunk_text
from app.vectordb.chroma_client import get_hrms_collection
from app.services.hrms_api_client import fetch_policy_from_api

collection = get_hrms_collection()

embedding_model = EmbeddingModel()


def get_policy_context(question: str):

    # Step 1: Try retrieving existing embeddings
    documents = retrieve_documents(question)

    if documents:
        return documents

    # Step 2: Fetch policy from API
    policy_text = fetch_policy_from_api()

    if not policy_text:
        return []

    # Step 3: Split policy into chunks
    chunks = chunk_text(policy_text)

    embeddings = []
    ids = []

    for i, chunk in enumerate(chunks):
        vector = embedding_model.embed_text(chunk)
        embeddings.append(vector)
        ids.append(f"leave_policy_{i}")

    # Step 4: Store chunks in ChromaDB
    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids
    )

    # Step 5: Retrieve again after indexing
    documents = retrieve_documents(question)

    return documents