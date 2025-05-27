from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from uuid import uuid4

from ollama import generate, embed
from embed.document_processor import preprocess_documents
from embed.vector_store import VectorStore

# === CONFIG ===
CHUNK_DIR = "T:/Code/Apps/Tars/android_docs_markdown_cleaned/"
EMBED_LIMIT = 100  # Limit number of document chunks to embed (for testing)
MAX_WORKERS = 8
EMBED_MODEL = "all-minilm:latest"
LLM_MODEL = "gemma3:4b-it-qat"

def generate_questions(chunk: str) -> list[str]:
    prompt = f"""
You are reading a developer documentation excerpt. Write 2-3 specific, clear questions that a developer might ask which could be answered using this content:

<CHUNK>
{chunk}
</CHUNK>

Format your questions like so:
1.
2.
3.
"""
    try:
        response = generate(model=LLM_MODEL, prompt=prompt)
        content = response["response"]
        return [q.strip() for q in content.split("\n") if q.strip().startswith(("1.", "2.", "3.", "4.", "5."))]
    except Exception as e:
        print(f"❌ Error generating questions: {e}")
        return []

def embed_question(question: str) -> list[float] | None:
    try:
        response = embed(model=EMBED_MODEL, input=question)
        return response["embeddings"][0]
    except Exception as e:
        print(f"❌ Error embedding question: {e}")
        return None

def main():
    print("📄 Processing documents...")
    chunks = preprocess_documents(CHUNK_DIR) #[:EMBED_LIMIT])
    print(f"Loaded {len(chunks)} chunks.")

    vector_db = VectorStore()
    embeddings_to_store = []
    metadatas_to_store = []
    ids_to_store = []

    print("🧠 Generating questions and embedding...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_chunk = {executor.submit(generate_questions, chunk): chunk for chunk in chunks}

        for future in tqdm(as_completed(future_to_chunk), total=len(future_to_chunk), desc="Processing chunks"):
            chunk = future_to_chunk[future]
            questions = future.result()

            for q in questions:
                vector = embed_question(q)
                if vector:
                    embeddings_to_store.append(vector)
                    metadatas_to_store.append({
                        "question": q,
                        "source_chunk": chunk
                    })
                    ids_to_store.append(uuid4().hex)

    vector_db.add_documents(metadatas_to_store, embeddings_to_store, ids_to_store)

    print(f"✅ Done. Stored {len(embeddings_to_store)} question embeddings in vector DB.")

if __name__ == "__main__":
    main()
