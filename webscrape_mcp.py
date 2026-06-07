#!/usr/bin/env python3
'''
MCP Server for Web Scraping.

Provides AI agents with the ability to fetch and extract clean content
from web pages. Converts HTML to clean Markdown for LLM consumption.
'''

from typing import Optional, List
from enum import Enum
import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

import os

mcp = FastMCP("webscrape_mcp")
mcp.settings.host = os.environ.get("HOST", "127.0.0.1")
mcp.settings.port = int(os.environ.get("PORT", "8000"))

_cache: dict = {}
_CACHE_MAX = 200

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"

class SearchSource(str, Enum):
    DUCKDUCKGO = "duckduckgo"
    GOOGLE = "google"

class FetchUrlInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: str = Field(..., description="URL to fetch (e.g., 'https://example.com/page')", min_length=5, max_length=4096)
    selector: Optional[str] = Field(default=None, description="CSS selector to extract a specific element (e.g., 'article.main-content', '#post-content')")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")
    max_chars: int = Field(default=10000, description="Maximum characters to return", ge=500, le=100000)
    use_readability: bool = Field(default=False, description="Use Mozilla Readability for better article extraction (removes nav/sidebars/ads automatically)")
    render_js: bool = Field(default=False, description="Render JavaScript with Playwright before extracting (use for SPAs, React, Vue sites)")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v

class BatchFetchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    urls: List[str] = Field(..., description="List of URLs to fetch (max 5)", min_length=1, max_length=5)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")
    max_chars_per_url: int = Field(default=5000, description="Maximum characters per URL", ge=500, le=50000)

    @field_validator('urls')
    @classmethod
    def validate_urls(cls, v: List[str]) -> List[str]:
        for url in v:
            if not url.startswith(('http://', 'https://')):
                raise ValueError(f"URL must start with http:// or https://: {url}")
        return v

async def _fetch_page(url: str, selector: Optional[str] = None, timeout: int = 30, use_readability: bool = False) -> dict:
    cache_key = f"{url}:{selector}:{use_readability}"
    if cache_key in _cache:
        return _cache[cache_key]
    import random
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")

        if "application/pdf" in content_type or url.lower().endswith(".pdf"):
            import fitz
            pdf_doc = fitz.open(stream=response.content, filetype="pdf")
            text = "".join(page.get_text() for page in pdf_doc)
            pdf_doc.close()
            filename = url.split("/")[-1].replace(".pdf", "")
            result = {
                "url": url,
                "title": filename,
                "content": text,
                "content_type": "text/markdown",
                "word_count": len(text.split()),
            }
            _cache[cache_key] = result
            return result

        if "text/html" not in content_type and "application/xhtml" not in content_type:
            result = {
                "url": url,
                "title": "",
                "content": response.text[:2000],
                "content_type": content_type,
                "word_count": 0,
            }
            _cache[cache_key] = result
            return result

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        if selector:
            elements = soup.select(selector)
            if not elements:
                return {
                    "url": url,
                    "title": title,
                    "content": "",
                    "error": f"No elements matched selector '{selector}'",
                }
            raw_html = "".join(str(el) for el in elements)
        elif use_readability:
            from readability import Document
            doc = Document(response.text)
            raw_html = doc.summary()
        else:
            for unwanted in soup.select("script, style, nav, footer, header, iframe, .sidebar, .advertisement, .menu, noscript"):
                unwanted.decompose()
            body = soup.find("body") or soup
            raw_html = str(body)

        markdown_content = md(raw_html, heading_style="ATX", bullets="-", strip=["img", "a"])
        lines = [line for line in markdown_content.split("\n") if line.strip()]
        markdown_content = "\n".join(lines)
        result = {
            "url": url,
            "title": title,
            "content": markdown_content,
            "content_type": "text/markdown",
            "word_count": len(markdown_content.split()),
        }
    _cache[cache_key] = result
    if len(_cache) > _CACHE_MAX:
        for k in list(_cache)[:50]:
            del _cache[k]
    return result

_pw_browser = None

async def _get_browser():
    global _pw_browser
    if _pw_browser is None:
        from playwright.async_api import async_playwright
        p = await async_playwright().__aenter__()
        _pw_browser = await p.chromium.launch(headless=True)
    return _pw_browser

async def _fetch_page_playwright(url: str, timeout: int = 30) -> dict:
    cache_key = f"pw:{url}"
    if cache_key in _cache:
        return _cache[cache_key]
    browser = await _get_browser()
    page = await browser.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
        title = await page.title()
        content = await page.content()
        text_content = await page.evaluate("document.body.innerText")
    finally:
        await page.close()
    title = title.strip() if title else ""
    lines = [line for line in text_content.split("\n") if line.strip()]
    result = {
        "url": url,
        "title": title,
        "content": "\n".join(lines),
        "content_type": "text/markdown",
        "word_count": len(text_content.split()),
    }
    _cache[cache_key] = result
    if len(_cache) > _CACHE_MAX:
        for k in list(_cache)[:50]:
            del _cache[k]
    return result

def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 403:
            return f"Error: Access denied (403). The server blocked the request. Try a different URL."
        elif status == 404:
            return f"Error: Page not found (404). Check the URL."
        elif status == 429:
            return f"Error: Rate limited (429). Try again later."
        elif status >= 500:
            return f"Error: Server error ({status}). The website may be down."
        return f"Error: HTTP {status} fetching page."
    elif isinstance(e, httpx.TimeoutException):
        return f"Error: Request timed out. The page took too long to respond."
    elif isinstance(e, httpx.ConnectError):
        return f"Error: Could not connect to the server. Check the URL or your internet connection."
    return f"Error: {type(e).__name__}: {str(e)}"

@mcp.tool(
    name="webscrape_fetch_url",
    annotations={
        "title": "Fetch Web Page Content",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def webscrape_fetch_url(params: FetchUrlInput) -> str:
    '''Fetch a web page and return its content as clean Markdown.

    Extracts the main content from any public URL, removes clutter (nav, ads, scripts),
    and converts to clean Markdown formatted for LLM consumption.

    Supports:
    - Regular HTML pages converted to clean Markdown
    - PDF files: text extraction with PyMuPDF (auto-detected by URL or content-type)
    - Readability mode: uses Mozilla Readability for article-focused extraction
    - JS rendering: Playwright-based rendering for SPAs (React, Vue, Angular)

    Args:
        params (FetchUrlInput): Validated input parameters containing:
            - url (str): The full URL to fetch (required)
            - selector (Optional[str]): CSS selector to target a specific page element
            - response_format (ResponseFormat): 'markdown' (default) or 'json'
            - max_chars (int): Maximum characters to return (default 10000, max 100000)
            - use_readability (bool): Use Mozilla Readability for cleaner article extraction (default False)
            - render_js (bool): Render JavaScript with Playwright before extracting (default False)

    Returns:
        str: Page content in Markdown or JSON format.

    Examples:
        - Fetch a blog post: url="https://example.com/blog/post"
        - Fetch with selector: url="https://example.com", selector="main.content"
        - Fetch as JSON: url="https://example.com", response_format="json"
        - Fetch with readability: url="https://example.com/article", use_readability=True
        - Fetch with JS rendering: url="https://example.com/spa", render_js=True
        - Fetch a PDF: url="https://example.com/document.pdf"

    Error Handling:
        - Returns clear error for 403 (blocked), 404 (not found), 429 (rate limited)
        - Returns error for timeouts and connection failures
    '''
    try:
        if params.render_js:
            result = await _fetch_page_playwright(params.url)
        else:
            result = await _fetch_page(params.url, params.selector, use_readability=params.use_readability)
        if "error" in result:
            return result["error"]

        content = result["content"]
        if len(content) > params.max_chars:
            content = content[:params.max_chars] + f"\n\n[... truncated at {params.max_chars} characters]"

        if params.response_format == ResponseFormat.JSON:
            import json
            return json.dumps({
                "title": result["title"],
                "url": result["url"],
                "word_count": result["word_count"],
                "content": content,
            }, indent=2)

        header = f"# {result['title']}\n\n" if result["title"] else ""
        meta = f"*Source: {result['url']}*  \n*Words: {result['word_count']}*\n\n---\n\n"
        return f"{header}{meta}{content}"

    except Exception as e:
        return _handle_error(e)

@mcp.tool(
    name="webscrape_batch_fetch",
    annotations={
        "title": "Fetch Multiple Web Pages",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def webscrape_batch_fetch(params: BatchFetchInput) -> str:
    '''Fetch multiple web pages in parallel and return their content.

    Efficiently scrapes up to 5 URLs simultaneously. Each page is cleaned
    and converted to Markdown. Results are separated by page.
    Supports PDF text extraction (auto-detected).

    Args:
        params (BatchFetchInput): Validated input parameters containing:
            - urls (List[str]): Array of URLs to fetch (1-5 URLs)
            - response_format (ResponseFormat): 'markdown' (default) or 'json'
            - max_chars_per_url (int): Max characters per URL (default 5000)

    Returns:
        str: Combined content from all pages in Markdown or JSON format.

    Examples:
        - Compare two articles: urls=["https://example.com/a", "https://example.com/b"]
    '''
    import asyncio
    try:
        tasks = [_fetch_page(url, timeout=30) for url in params.urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        if params.response_format == ResponseFormat.JSON:
            import json
            output = []
            for url, result in zip(params.urls, results):
                if isinstance(result, Exception):
                    output.append({"url": url, "error": str(result)})
                else:
                    content = result["content"][:params.max_chars_per_url]
                    output.append({
                        "url": result["url"],
                        "title": result["title"],
                        "word_count": result["word_count"],
                        "content": content,
                    })
            return json.dumps(output, indent=2)

        parts = []
        for url, result in zip(params.urls, results):
            if isinstance(result, Exception):
                parts.append(f"## Failed: {url}\n\n{_handle_error(result)}\n")
            else:
                content = result["content"][:params.max_chars_per_url]
                title = result["title"] or url
                parts.append(f"# {title}\n\n*Source: {result['url']}*\n\n{content}\n")
        return "\n---\n\n".join(parts)

    except Exception as e:
        return _handle_error(e)

class SearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(..., description="Search query (e.g., 'latest AI news 2026', 'Python async tutorial')", min_length=2, max_length=500)
    max_results: int = Field(default=5, description="Number of search results to fetch and scrape", ge=1, le=10)
    max_chars_per_result: int = Field(default=3000, description="Maximum characters per scraped result", ge=500, le=20000)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format")
    search_source: SearchSource = Field(default=SearchSource.DUCKDUCKGO, description="Search engine to use: 'duckduckgo' (default, no key) or 'google' (free scraping)")

async def _search_duckduckgo(query: str, max_results: int) -> list:
    import asyncio
    loop = asyncio.get_event_loop()
    def search_sync():
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        return results
    return await loop.run_in_executor(None, search_sync)

async def _search_google(query: str, max_results: int) -> list:
    import asyncio
    loop = asyncio.get_event_loop()
    def search_sync():
        from googlesearch import search
        results = []
        for r in search(query, num_results=max_results, advanced=True):
            results.append({
                "title": r.title,
                "url": r.url,
                "snippet": r.description,
            })
        return results
    return await loop.run_in_executor(None, search_sync)

async def _search_web(query: str, max_results: int, source: SearchSource = SearchSource.DUCKDUCKGO) -> list:
    if source == SearchSource.GOOGLE:
        return await _search_google(query, max_results)
    return await _search_duckduckgo(query, max_results)

@mcp.tool(
    name="webscrape_search",
    annotations={
        "title": "Search Web and Scrape Results",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def webscrape_search(params: SearchInput) -> str:
    '''Search the web for a query and scrape the top results into clean Markdown.

    Combines search with content scraping in one step. Returns
    search result snippets plus the full page content of each result.
    Supports PDF text extraction (auto-detected).

    Search sources:
    - duckduckgo (default): no API key required, free
    - google: free scraping, no API key required

    Args:
        params (SearchInput): Validated input parameters containing:
            - query (str): Search query (e.g., 'latest AI news 2026')
            - max_results (int): Number of results to scrape (1-10, default 5)
            - max_chars_per_result (int): Max chars per scraped page (default 3000)
            - response_format (ResponseFormat): 'markdown' (default) or 'json'
            - search_source (SearchSource): 'duckduckgo' (default) or 'google'

    Returns:
        str: Search results with scraped content in Markdown or JSON format.

    Examples:
        - Research: query="Python async programming best practices", max_results=3
        - News: query="latest AI developments 2026", max_results=5
        - Google search: query="latest tech news", search_source="google"
    '''
    import asyncio
    try:
        results = await _search_web(params.query, params.max_results, source=params.search_source)
        if not results:
            return f"No results found for '{params.query}'"

        tasks = []
        for r in results:
            if r["url"]:
                tasks.append(_fetch_page(r["url"], timeout=20))

        scraped = await asyncio.gather(*tasks, return_exceptions=True)

        if params.response_format == ResponseFormat.JSON:
            import json
            output = []
            for i, r in enumerate(results):
                entry = {
                    "title": r["title"],
                    "url": r["url"],
                    "snippet": r["snippet"],
                }
                if i < len(scraped) and not isinstance(scraped[i], Exception):
                    entry["content"] = scraped[i]["content"][:params.max_chars_per_result]
                else:
                    entry["content"] = ""
                output.append(entry)
            return json.dumps(output, indent=2)

        parts = [f"# Search: {params.query}", f"*{len(results)} results found via {params.search_source.value}*\n"]
        for i, r in enumerate(results):
            parts.append(f"## {i+1}. {r['title']}")
            parts.append(f"**URL:** {r['url']}")
            parts.append(f"**Snippet:** {r['snippet']}\n")
            if i < len(scraped) and not isinstance(scraped[i], Exception):
                content = scraped[i]["content"][:params.max_chars_per_result]
                parts.append(content + "\n")

        return "\n".join(parts)

    except Exception as e:
        return _handle_error(e)

class ScreenshotInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    url: str = Field(..., description="URL to capture", min_length=5, max_length=4096)
    full_page: bool = Field(default=True, description="Capture full page (True) or viewport only (False)")
    width: int = Field(default=1280, description="Viewport width in pixels", ge=320, le=3840)
    height: int = Field(default=720, description="Viewport height in pixels", ge=240, le=2160)

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v

@mcp.tool(
    name="webscrape_screenshot",
    annotations={
        "title": "Capture Screenshot of Web Page",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def webscrape_screenshot(params: ScreenshotInput) -> str:
    '''Take a screenshot of a web page and return it as a base64 data URI.

    Useful for capturing visual content: dashboards, charts, graphs,
    UI previews, and any page where visual layout matters.

    Args:
        params (ScreenshotInput): Validated input parameters containing:
            - url (str): The URL to capture
            - full_page (bool): Capture full page or viewport only (default True)
            - width (int): Viewport width in pixels (default 1280)
            - height (int): Viewport height in pixels (default 720)

    Returns:
        str: Markdown image tag with base64-encoded PNG data URI.

    Examples:
        - Capture dashboard: url="https://example.com/dashboard"
        - Capture with custom viewport: url="https://example.com", width=1920, height=1080
    '''
    try:
        browser = await _get_browser()
        page = await browser.new_page(viewport={"width": params.width, "height": params.height})
        try:
            await page.goto(params.url, wait_until="networkidle", timeout=30000)
            if params.full_page:
                screenshot_bytes = await page.screenshot(full_page=True, type="png")
            else:
                screenshot_bytes = await page.screenshot(type="png")
        finally:
            await page.close()

        import base64
        b64 = base64.b64encode(screenshot_bytes).decode()
        return f"![Screenshot of {params.url}](data:image/png;base64,{b64})"
    except Exception as e:
        return f"Error taking screenshot: {type(e).__name__}: {str(e)}"

if __name__ == "__main__":
    import sys
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    mcp.run(transport=transport)
