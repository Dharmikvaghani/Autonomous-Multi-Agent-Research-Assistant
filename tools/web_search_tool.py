"""
Web Search Tool Module
Provides real-time internet search capability powered by the DuckDuckGo Search API (DDGS).
Used by AI agents to fetch up-to-date facts and references on any research topic.
"""

import logging
try:
    from duckduckgo_search import DDGS
except ImportError:
    from ddgs import DDGS

# Setup module-level logger
logger = logging.getLogger(__name__)

def search_web(query: str) -> list:
    """
    Searches the web for the given query using the DuckDuckGo Search API.
    
    Args:
        query (str): The search query text.
        
    Returns:
        list: A list of dicts, each containing:
              - 'title': Page title
              - 'snippet': Short text snippet from the page
              - 'url': Link to the page
    """
    if not query or not query.strip():
        logger.warning("Empty search query provided.")
        return []

    print(f"[*] Web Search: Querying DuckDuckGo for: '{query}'...")
    try:
        # Query DDGS for text matches
        with DDGS() as ddgs:
            # Fetch up to 5 results
            raw_results = list(ddgs.text(query, max_results=5))
            
            # Format and normalize the search result objects
            formatted_results = []
            for r in raw_results:
                title = r.get("title", "No Title").strip()
                snippet = r.get("body", "No Snippet").strip()
                url = r.get("href", "#").strip()
                
                formatted_results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": url
                })
            
            print(f"[*] Web Search: Successfully retrieved {len(formatted_results)} results.")
            return formatted_results
            
    except Exception as e:
        # Gracefully handle API limits, network timeouts, or schema changes
        print(f"[!] Web Search Error: Failed to complete search. Detail: {e}")
        logger.error(f"DuckDuckGo search error: {e}", exc_info=True)
        return []

def format_search_results(results: list) -> str:
    """
    Formats a list of web search results into a clean, markdown-friendly text block.
    
    Args:
        results (list): The list of dictionaries returned by search_web.
        
    Returns:
        str: A formatted markdown block containing the search titles, summaries, and source URLs.
    """
    if not results:
        return "No real-time web search results available."
        
    formatted = "### REAL-TIME WEB CONTEXT & RECENT DEVELOPMENTS ###\n\n"
    for idx, r in enumerate(results):
        formatted += f"[{idx + 1}] Title: {r['title']}\n"
        formatted += f"    Source URL: {r['url']}\n"
        formatted += f"    Snippet: {r['snippet']}\n\n"
        
    formatted += "--- Please reference and integrate the above latest facts and source URLs directly into the appropriate sections of your research report. ---\n"
    return formatted

# Self-testing block
if __name__ == "__main__":
    print("=== Testing DuckDuckGo Web Search Tool ===")
    test_query = "Latest LLM models released in 2026"
    results = search_web(test_query)
    
    if results:
        print("\n" + format_search_results(results))
    else:
        print("\nFailed to retrieve search results.")
