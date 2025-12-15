# =============================================================================
# OSINT News Aggregator - Search Tools
# =============================================================================
"""
Web search tools for OSINT operations.

Provides:
- TavilySearchTool: AI-powered search with Tavily API
- DuckDuckGoSearchTool: Free search without API key
- GoogleDorkBuilderTool: Advanced Google dorking queries
"""

import os
import json
import asyncio
import logging
from typing import Optional, Type
from urllib.parse import quote_plus

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

from tools.base import WebSearchInput, GoogleDorkInput

logger = logging.getLogger(__name__)


# =============================================================================
# Tavily Search Tool
# =============================================================================

class TavilySearchTool(BaseTool):
    """
    Tavily AI-powered web search tool.
    
    Requires TAVILY_API_KEY environment variable.
    Best for: current events, news, technical documentation, research.
    """
    
    name: str = "tavily_search"
    description: str = """Search the web using Tavily AI-powered search engine.
    Best for: current events, news, technical documentation, research.
    Returns: title, URL, content snippet, and relevance score for each result."""
    args_schema: Type[BaseModel] = WebSearchInput
    
    def _run(
        self,
        query: str,
        max_results: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute Tavily search synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop in thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(query, max_results, run_manager)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(
                    self._arun(query, max_results, run_manager)
                )
        except RuntimeError:
            return asyncio.run(self._arun(query, max_results, run_manager))
    
    async def _arun(
        self,
        query: str,
        max_results: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute Tavily search asynchronously."""
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        
        if not tavily_key:
            return json.dumps({
                "error": "TAVILY_API_KEY not configured",
                "results": []
            })
        
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=tavily_key)
            response = client.search(
                query=query,
                search_depth="advanced",
                max_results=min(max_results, 20),
                include_answer=True,
                include_raw_content=True
            )
            
            results = []
            
            # Include AI-generated answer
            if response.get("answer"):
                results.append({
                    "type": "ai_summary",
                    "title": f"AI Analysis: {query[:50]}",
                    "content": response["answer"],
                    "url": "",
                    "score": 1.0
                })
            
            # Include search results
            for item in response.get("results", []):
                results.append({
                    "type": "search_result",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "score": item.get("score", 0)
                })
            
            return json.dumps({
                "query": query,
                "count": len(results),
                "results": results
            })
            
        except ImportError:
            return json.dumps({
                "error": "tavily package not installed. Run: pip install tavily-python",
                "results": []
            })
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return json.dumps({"error": str(e), "results": []})


# =============================================================================
# DuckDuckGo Search Tool
# =============================================================================

class DuckDuckGoSearchTool(BaseTool):
    """
    DuckDuckGo web search tool.
    
    No API key required - uses HTML scraping.
    Best for: general web searches when Tavily is not available.
    """
    
    name: str = "duckduckgo_search"
    description: str = """Search the web using DuckDuckGo.
    Best for: general web searches when Tavily is not available.
    No API key required. Returns: title, URL, and snippet for each result."""
    args_schema: Type[BaseModel] = WebSearchInput
    
    def _run(
        self,
        query: str,
        max_results: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute DuckDuckGo search synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(query, max_results, run_manager)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(
                    self._arun(query, max_results, run_manager)
                )
        except RuntimeError:
            return asyncio.run(self._arun(query, max_results, run_manager))
    
    async def _arun(
        self,
        query: str,
        max_results: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Execute DuckDuckGo search asynchronously."""
        results = []
        
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'lxml')
                        
                        for div in soup.find_all('div', class_='result')[:max_results]:
                            try:
                                title_elem = div.find('a', class_='result__a')
                                if not title_elem:
                                    continue
                                
                                title = title_elem.get_text(strip=True)
                                href = title_elem.get('href', '')
                                
                                snippet_elem = div.find('a', class_='result__snippet')
                                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                                
                                if title and href:
                                    results.append({
                                        "title": title,
                                        "url": href,
                                        "content": snippet,
                                        "score": 0.5
                                    })
                            except Exception as e:
                                logger.debug(f"Error parsing result: {e}")
                                continue
            
            return json.dumps({
                "query": query,
                "count": len(results),
                "results": results
            })
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return json.dumps({"error": str(e), "results": []})


# =============================================================================
# Google Dork Builder Tool
# =============================================================================

class GoogleDorkBuilderTool(BaseTool):
    """
    Google dork query builder tool.
    
    Constructs advanced Google search queries using dork operators.
    Does not execute search - returns the constructed query.
    """
    
    name: str = "google_dork_builder"
    description: str = """Build advanced Google dork queries.
    Combines search operators like site:, filetype:, intitle:, inurl:.
    Returns the constructed query for use with other search tools."""
    args_schema: Type[BaseModel] = GoogleDorkInput
    
    def _run(
        self,
        base_query: str,
        site: Optional[str] = None,
        filetype: Optional[str] = None,
        intitle: Optional[str] = None,
        inurl: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Build and return a Google dork query."""
        parts = [base_query]
        
        if site:
            parts.append(f'site:{site}')
        if filetype:
            parts.append(f'filetype:{filetype}')
        if intitle:
            parts.append(f'intitle:"{intitle}"')
        if inurl:
            parts.append(f'inurl:{inurl}')
        
        dork_query = ' '.join(parts)
        
        return json.dumps({
            "dork_query": dork_query,
            "components": {
                "base": base_query,
                "site": site,
                "filetype": filetype,
                "intitle": intitle,
                "inurl": inurl
            }
        })
    
    async def _arun(
        self,
        base_query: str,
        site: Optional[str] = None,
        filetype: Optional[str] = None,
        intitle: Optional[str] = None,
        inurl: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Async version of dork builder."""
        return self._run(base_query, site, filetype, intitle, inurl, run_manager)
