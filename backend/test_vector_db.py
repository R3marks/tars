# check_vector_db.py
from embed.vector_store import VectorStore

store = VectorStore()
print(f"Collection has {store.collection.count()} documents.")

results = store.collection.peek()
print(results)
print("Sample stored doc:", results["documents"][0])
