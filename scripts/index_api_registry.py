from app.vectordb.api_vector_store import APIVectorStore

store = APIVectorStore()
store.index_tools()

print("API registry indexed successfully")