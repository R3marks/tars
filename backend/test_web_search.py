import asyncio
from search.web_search import crawl_page_markdown

async def test():
    markdown = await crawl_page_markdown("https://forum.wordreference.com/threads/abbreviation-of-number-n-n%C2%B0-nr-nbr-no.264328/")
    print(markdown)

asyncio.run(test())
