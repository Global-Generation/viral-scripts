from config import TAVILY_API_KEY
from tavily import TavilyClient

_client = None


def get_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=TAVILY_API_KEY)
    return _client


def search_tiktok(query: str, max_results: int = 15) -> list[dict]:
    client = get_client()
    response = client.search(
        query=query,
        search_depth="basic",
        include_domains=["tiktok.com"],
        max_results=max_results,
    )
    results = response.get("results", [])
    return [r for r in results if "/video/" in r.get("url", "")]
