from ollama import embed
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from embed.document_processor import preprocess_documents
from embed.vector_store import VectorStore


def embed_chunk(chunk):
    try:
        response = embed(model="all-minilm:latest", input=chunk)
        return response["embeddings"][0]
    except Exception as e:
        print(f"Error embedding chunk: {e}")
        return None


def main():
    print("Processing documents...")
    chunks = preprocess_documents("T:/Code/Apps/Tars/android_docs_text")
    print(f"{len(chunks)} text chunks loaded.")

    print("Embedding and storing documents...")

    embedded_vectors = []
    valid_chunks = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(embed_chunk, chunk): chunk for chunk in chunks}

        for future in tqdm(as_completed(futures), total=len(futures), desc="Embedding"):
            vector = future.result()
            if vector is not None:
                embedded_vectors.append(vector)
                valid_chunks.append(futures[future])  # Store corresponding chunk

    ids = [f"doc_{i}" for i in range(len(valid_chunks))]

    vector_db = VectorStore()
    vector_db.add_documents(valid_chunks, embedded_vectors, ids)

    print("✅ Done. Vector DB ready.")


if __name__ == "__main__":
    main()
