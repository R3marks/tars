import asyncio
from crawl4ai import AsyncWebCrawler
from ddgs import DDGS
from ollama import chat
import time

def run_web_search(query: str, max_results: int = 3) -> list[dict]:
    query = query.strip("search")
    print(query)
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            if r and all(k in r for k in ("title", "body", "href")):
                results.append({
                    "title": r["title"],
                    "snippet": r["body"],
                    "url": r["href"]
                })
    return results

def select_best_link(question: str, links: list[dict]) -> dict:
    formatted_links = "\n\n".join(
        f"[{i+1}] {link['title']}\n{link['snippet']}" for i, link in enumerate(links)
    )
    selection_prompt = (
        "You're helping select the most useful web result to answer a user's question.\n\n"
        f"Question: {question}\n\n"
        f"Web Results:\n{formatted_links}\n\n"
        "Respond with the number of the best link to follow."
    )

    start_time = time.time()

    response = chat(
        model="qwen3:0.6b",  # any small fast model
        messages=[{ 
            "role": "user", 
            "content": selection_prompt 
        }],
        think=False
    )

    elapsed = time.time() - start_time
    print(f"⏱️ Link chooser LLM response time: {elapsed:.2f} seconds")

    try:
        choice = int(response.message.content.strip().split()[0])
        return links[choice - 1]
    except:
        return links[0]  # fallback
    
async def crawl_page_markdown(url: str) -> str:
    async with AsyncWebCrawler() as crawler:
        print(url)
        result = await crawler.arun(url=url)
        return result.markdown
