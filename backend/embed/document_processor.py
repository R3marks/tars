import os
import re
from textwrap import wrap
from typing import List

def load_text_files(folder_path: str) -> List[str]:
    documents = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            with open(os.path.join(folder_path, filename), "r", encoding="utf-8") as f:
                text = f.read()
                documents.append(text)
    return documents

def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\n{2,}", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text

def chunk_text(text: str, max_length: int = 500) -> List[str]:
    return wrap(text, max_length)

def preprocess_documents(folder_path: str, chunk_size: int = 500) -> List[str]:
    raw_docs = load_text_files(folder_path)
    cleaned_chunks = []
    for doc in raw_docs:
        cleaned = clean_text(doc)
        chunks = chunk_text(cleaned, max_length=chunk_size)
        cleaned_chunks.extend(chunks)
    return cleaned_chunks
