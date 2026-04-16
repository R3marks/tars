import logging
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler
from ddgs import DDGS
from ollama import chat

logger = logging.getLogger("uvicorn.error")

def check_if_search_is_needed(query: str) -> bool:
    """Check if web browsing is needed based on the query context."""
    
    # LLM prompt for analysis
    analysis_prompt = (
        f"""
        You are a router LLM. Analyze the following query in flow:\n\n"
        Query: {query}\n\n'
        "To help answer this query, do you need to search the web to search for more context? If yes, return True; if no, return False.\n\n
        Examples:
        "What is the temperature today in London -> return True"\n
        "What is 5 * 10 -> return False\n

        """
    )
    
    # Use the Qwen 3.0.6B model for analysis
    model = "qwen3:0.6b"
    
    # Initialize the chat with the analysis prompt
    response = chat(
        model=model,  # Any small fast model
        messages=[
            {
                "role": "user",
                "content": analysis_prompt
            }
        ],
        think=False  # No thinking required
    )
    
    # Return the boolean result based on the LLM's response
    answer = response.message.content 
    print(answer)
    print(bool(answer))
    return bool(answer) and answer

def reformulate_query_into_internet_search(query: str) -> str:    
    # LLM prompt for analysis
    reformat_prompt = (
        f"""
        You are an LLM that transforms a base user query into a search query that will be directly supplied to DuckDuckGo online search.\n\n
        Analyse the following query carefully, identify what you need to search to best provide a response, and return the search query:\n\n
        Examples:
        "I want to know the weather in London tomorrow" -> "Weather in London tomorrow",\n
        "One of my most favourite films in Mission Impossible 3. Tom looks really young in that film. Do you know how old he was when he played the part? -> "Age of Tom Cruise during Mission Impossible 3"\n\n
        f'Query: {query}\n\n'
        """
    )
    
    # Use the Qwen 3 0.6B model for analysis
    model = "qwen3:0.6b"
    
    # Initialize the chat with the analysis prompt
    response = chat(
        model=model,  # Any small fast model
        messages=[
            {
                "role": "user",
                "content": reformat_prompt
            }
        ],
        think=False  # No thinking required
    )
    
    # Return the boolean result based on the LLM's response
    return response.message.content 

def run_web_search(query: str, max_results: int = 3) -> list[dict]:
    logger.info("Running web search for query: %s", query)

    try:
        results = run_ddgs_search(query, max_results)
        if results:
            logger.info("DDGS search returned %s results", len(results))
            return results
    except Exception:
        logger.exception("DDGS search failed for query: %s", query)

    fallback_results = run_duckduckgo_html_search(query, max_results)
    logger.info("Fallback HTML search returned %s results", len(fallback_results))
    return fallback_results


def run_ddgs_search(query: str, max_results: int) -> list[dict]:
    results = []

    with DDGS() as ddgs:
        for result in ddgs.text(query, max_results=max_results):
            if not result:
                continue

            if not all(key in result for key in ("title", "body", "href")):
                continue

            results.append({
                "title": result["title"],
                "snippet": result["body"],
                "url": result["href"],
            })

    return results


def run_duckduckgo_html_search(query: str, max_results: int) -> list[dict]:
    search_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"

    try:
        response = requests.get(
            search_url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Tars/0.1",
            },
        )
        response.raise_for_status()
    except Exception:
        logger.exception("DuckDuckGo HTML fallback search failed for query: %s", query)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for result_node in soup.select(".result"):
        title_link = result_node.select_one(".result__title a")
        snippet_node = result_node.select_one(".result__snippet")

        if title_link is None:
            continue

        title = title_link.get_text(" ", strip=True)
        snippet = "" if snippet_node is None else snippet_node.get_text(" ", strip=True)
        url = title_link.get("href", "").strip()

        if not title or not url:
            continue

        results.append({
            "title": title,
            "snippet": snippet,
            "url": url,
        })

        if len(results) >= max_results:
            break

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
