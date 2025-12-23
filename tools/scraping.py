# =============================================================================
# OSINT OA - Web Scraping Tools
# =============================================================================
"""
Web content scraping and extraction tools.

Provides:
- WebScraperTool: Extract content from web pages
"""

import json
import asyncio
import logging
from typing import Optional, Type, Dict, Any, List, ClassVar

import aiohttp
from bs4 import BeautifulSoup
from pydantic import BaseModel

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun

from tools.base import UrlInput

logger = logging.getLogger(__name__)


class WebScraperTool(BaseTool):
    """
    Web page content extraction tool.
    
    Extracts main content, metadata, and links from web pages.
    Useful for deep content analysis of search results.
    """
    
    name: str = "web_scraper"
    description: str = """Extract content from a web page.
    Retrieves: page title, main text content, meta description, and links.
    Best for: analyzing content of specific URLs found in searches."""
    args_schema: Type[BaseModel] = UrlInput
    
    def _run(
        self,
        url: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Scrape web page synchronously."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._arun(url, run_manager)
                    )
                    return future.result(timeout=60)
            else:
                return loop.run_until_complete(self._arun(url, run_manager))
        except RuntimeError:
            return asyncio.run(self._arun(url, run_manager))
    
    async def _arun(
        self,
        url: str,
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Scrape web page asynchronously."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                    ssl=False  # Some OSINT sites have cert issues
                ) as response:
                    if response.status != 200:
                        return json.dumps({
                            "error": f"HTTP {response.status}",
                            "url": url
                        })
                    
                    html = await response.text()
                    content = self._extract_content(html, url)
                    return json.dumps(content)
                    
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            return json.dumps({"error": str(e), "url": url})
    
    def _extract_content(self, html: str, url: str) -> Dict[str, Any]:
        """Extract structured content from HTML."""
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Extract title
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag:
            meta_desc = meta_tag.get('content', '')
        
        # Extract main content
        # Try to find article or main content areas
        main_content = ""
        for selector in ['article', 'main', '.content', '#content', '.post', '.entry']:
            content_elem = soup.select_one(selector)
            if content_elem:
                main_content = content_elem.get_text(separator=' ', strip=True)
                break
        
        # Fallback to body content
        if not main_content:
            body = soup.find('body')
            if body:
                main_content = body.get_text(separator=' ', strip=True)
        
        # Limit content length
        if len(main_content) > 5000:
            main_content = main_content[:5000] + "..."
        
        # Extract links
        links = []
        for a in soup.find_all('a', href=True)[:20]:
            href = a.get('href', '')
            text = a.get_text(strip=True)
            if href and text and not href.startswith('#'):
                links.append({"text": text[:100], "href": href})
        
        # Extract images
        images = []
        for img in soup.find_all('img', src=True)[:10]:
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
                images.append({"src": src, "alt": alt})
        
        return {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "content": main_content,
            "content_length": len(main_content),
            "links": links,
            "images": images
        }


class DorkQueryInput(BaseModel):
    """Input for Google dork query builder."""
    target: str
    dork_type: str = "basic"


class GoogleDorkBuilderTool(BaseTool):
    """
    Build Google dork queries for advanced OSINT searching.
    
    Creates specialized search queries using Google operators like
    site:, inurl:, intitle:, filetype:, etc.
    """
    
    name: str = "google_dork_builder"
    description: str = """Build advanced Google dork queries for OSINT.
    Input: target domain/topic and dork_type (basic, files, login, exposed, social).
    Output: List of dork queries to use with search engines.
    
    Examples:
    - target: "example.com", dork_type: "files" -> file discovery dorks
    - target: "company name", dork_type: "social" -> social media dorks
    """
    args_schema: Type[BaseModel] = DorkQueryInput
    
    # Dork templates by type
    DORK_TEMPLATES: ClassVar[Dict[str, List[str]]] = {
        "basic": [
            'site:{target}',
            '"{target}"',
            'intitle:"{target}"',
            'inurl:{target}',
        ],
        "files": [
            'site:{target} filetype:pdf',
            'site:{target} filetype:doc OR filetype:docx',
            'site:{target} filetype:xls OR filetype:xlsx',
            'site:{target} filetype:ppt OR filetype:pptx',
            'site:{target} filetype:txt',
            'site:{target} filetype:sql',
            'site:{target} filetype:log',
            'site:{target} filetype:bak',
        ],
        "login": [
            'site:{target} inurl:login',
            'site:{target} inurl:admin',
            'site:{target} inurl:wp-admin',
            'site:{target} intitle:"login"',
            'site:{target} inurl:signin',
            'site:{target} inurl:auth',
        ],
        "exposed": [
            'site:{target} "index of /"',
            'site:{target} intitle:"index of"',
            'site:{target} inurl:backup',
            'site:{target} inurl:config',
            'site:{target} ext:env OR ext:ini',
            'site:{target} "error" OR "warning" OR "mysql"',
        ],
        "social": [
            'site:linkedin.com "{target}"',
            'site:twitter.com "{target}"',
            'site:facebook.com "{target}"',
            'site:github.com "{target}"',
            'site:reddit.com "{target}"',
        ],
        "security": [
            'site:{target} "password" OR "passwd" OR "credentials"',
            'site:{target} "api_key" OR "apikey" OR "api-key"',
            'site:{target} "secret" OR "token"',
            'site:pastebin.com "{target}"',
            'site:ghostbin.com "{target}"',
        ],
    }
    
    def _run(
        self,
        target: str,
        dork_type: str = "basic",
        run_manager: Optional[CallbackManagerForToolRun] = None
    ) -> str:
        """Generate Google dork queries for the target."""
        templates = self.DORK_TEMPLATES.get(dork_type, self.DORK_TEMPLATES["basic"])
        
        dorks = []
        for template in templates:
            dork = template.format(target=target)
            dorks.append(dork)
        
        result = {
            "target": target,
            "dork_type": dork_type,
            "dorks": dorks,
            "usage": "Use these queries with DuckDuckGo or a search engine"
        }
        
        return json.dumps(result, indent=2)
