import chromadb
from chromadb.config import Settings
from ollama import embed

class VectorStore:
    def __init__(
            self, 
            persist_directory="./chroma_db_store", collection_name="android_docs"
            ):
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, documents, embeddings, ids):
        existing = self.collection.get(include=[])
        existing_ids = set(existing["ids"])

        new_docs = []
        new_embeds = []
        new_ids = []

        for doc, emb, id_ in zip(documents, embeddings, ids):
            if id_ not in existing_ids:
                new_docs.append(doc)
                new_embeds.append(emb)
                new_ids.append(id_)

        if new_docs:
            self.collection.add(
                documents=new_docs,
                embeddings=new_embeds,
                ids=new_ids
            )

    def query(self, query_text, n_results=5):
        response = embed(
            model="all-minilm:latest", 
            input=query_text)
        vector = response["embeddings"][0]
    
        return self.collection.query(
            query_embeddings=[vector],
            n_results=n_results,
            include=["documents", "distances"]
        )
