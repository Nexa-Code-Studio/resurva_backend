import os
import re
from html import unescape
from urllib.parse import unquote, quote_plus
from typing import Any
import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import UserRole
from app.mcp.base_tool import BaseMCPTool


class WebSearchAndCrawlInput(BaseModel):
    query: str = Field(description="Search query to find external information (e.g. food waste statistics, business marketing strategies).")
    url_to_crawl: str | None = Field(None, description="Optional URL to scrape details from directly (retrieved from search results).")


class WebSearchAndCrawlTool(BaseMCPTool):
    name = "web_search_and_crawl"
    description = "Searches the web for business strategies, market insights, and crawls/scrapes specific webpages for details."
    input_schema = WebSearchAndCrawlInput
    allowed_roles = [UserRole.OWNER, UserRole.ADMIN, UserRole.SELLER]

    async def execute(
        self,
        db: AsyncSession,
        query: str,
        url_to_crawl: str | None = None
    ) -> dict[str, Any]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # If a URL is explicitly requested to crawl
        crawled_content = None
        if url_to_crawl:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(url_to_crawl, headers=headers)
                    if resp.status_code == 200:
                        html = resp.text
                        # Strip script and style tags
                        html_clean = re.sub(r'<(script|style|header|footer|nav)[^>]*>[\s\S]*?</\1>', '', html)
                        # Strip all other HTML tags
                        text = re.sub(r'<[^>]+>', ' ', html_clean)
                        # Unescape HTML entities
                        text = unescape(text)
                        # Clean up whitespace
                        text = re.sub(r'\s+', ' ', text).strip()
                        crawled_content = text[:4000] + "..." if len(text) > 4000 else text
                    else:
                        crawled_content = f"Error: Status code {resp.status_code}"
            except Exception as e:
                crawled_content = f"Error while crawling page: {str(e)}"

        # Perform Search
        search_results = []
        tavily_key = os.getenv("TAVILY_API_KEY")

        if tavily_key:
            # Use Tavily API
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    tavily_resp = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": tavily_key,
                            "query": query,
                            "search_depth": "basic",
                            "include_answer": False,
                            "max_results": 5
                        }
                    )
                    if tavily_resp.status_code == 200:
                        data = tavily_resp.json()
                        for r in data.get("results", []):
                            search_results.append({
                                "title": r.get("title"),
                                "url": r.get("url"),
                                "snippet": r.get("content")
                            })
                    else:
                        # Fallback to DuckDuckGo if Tavily failed
                        search_results = await self._ddg_fallback(query, headers)
            except Exception:
                search_results = await self._ddg_fallback(query, headers)
        else:
            # Fallback to DuckDuckGo HTML Scraper
            search_results = await self._ddg_fallback(query, headers)

        return {
            "query": query,
            "search_results": search_results,
            "crawled_url": url_to_crawl,
            "crawled_content": crawled_content
        }

    async def _ddg_fallback(self, query: str, headers: dict[str, str]) -> list[dict[str, str]]:
        results = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    html = resp.text
                    result_blocks = re.findall(r'<div class="[^"]*web-result[^"]*">([\s\S]*?)</div>\s*</div>', html)
                    for block in result_blocks[:5]:
                        title_match = re.search(r'<a class="result__url"[^>]*>([\s\S]*?)</a>', block)
                        url_match = re.search(r'href="([^"]*)"', block)
                        snippet_match = re.search(r'<a class="result__snippet"[^>]*>([\s\S]*?)</a>', block)
                        
                        if title_match and url_match:
                            title = unescape(re.sub(r'<[^>]+>', '', title_match.group(1)).strip())
                            raw_url = url_match.group(1)
                            
                            actual_url = raw_url
                            if "/l/?uddg=" in raw_url:
                                actual_url = unquote(raw_url.split("/l/?uddg=")[1].split("&")[0])
                            elif "uddg=" in raw_url:
                                actual_url = unquote(raw_url.split("uddg=")[1].split("&")[0])
                                
                            snippet = ""
                            if snippet_match:
                                snippet = unescape(re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip())
                                
                            results.append({
                                "title": title,
                                "url": actual_url,
                                "snippet": snippet
                            })
        except Exception:
            pass
        return results
