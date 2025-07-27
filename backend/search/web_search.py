from crawl4ai import AsyncWebCrawler
from ddgs import DDGS
from ollama import chat
import time

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
