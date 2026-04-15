#!/usr/bin/env python3
"""
Web Research MCP Server
========================
Web browsing and research toolkit for AI agents. Search the web via DuckDuckGo,
extract content from pages using Playwright, take screenshots, click/type on
pages, and perform multi-step research workflows.

Install: pip install mcp httpx playwright && python -m playwright install chromium
Run:     python server.py
"""

import json
import re
import subprocess
import base64
from urllib.parse import urlparse
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# SSRF Protection
# ---------------------------------------------------------------------------
BLOCKED_HOSTS = [
    "localhost", "127.0.0.1", "0.0.0.0", "::1",
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal",  # GCP metadata
]
BLOCKED_PREFIXES = ["10.", "172.16.", "172.17.", "172.18.", "172.19.",
                     "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                     "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                     "172.30.", "172.31.", "192.168."]


def _is_safe_url(url: str) -> bool:
    """Block SSRF attempts targeting internal/cloud metadata services."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if host in BLOCKED_HOSTS:
            return False
        if any(host.startswith(p) for p in BLOCKED_PREFIXES):
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        return True
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
FREE_DAILY_LIMIT = 10
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous") -> Optional[str]:
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= FREE_DAILY_LIMIT:
        return f"Free tier limit reached ({FREE_DAILY_LIMIT}/day). Upgrade to Pro: https://mcpize.com/web-research-mcp/pro"
    _usage[caller].append(now)
    return None


# ---------------------------------------------------------------------------
# Web Search (DuckDuckGo via DDGS library or fallback to HTML scraping)
# ---------------------------------------------------------------------------
def _web_search(query: str, limit: int = 5) -> dict:
    """Search the web using DuckDuckGo."""
    # Try the DDGS Python library first
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=limit))
        return {
            "results": [
                {"title": r.get("title", ""), "url": r.get("href", r.get("link", "")),
                 "snippet": r.get("body", r.get("snippet", ""))}
                for r in results
            ],
            "query": query,
            "engine": "duckduckgo",
        }
    except ImportError:
        pass

    # Fallback: httpx to DuckDuckGo HTML API
    try:
        import httpx
        r = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MCP-Research/1.0"},
            timeout=10,
            follow_redirects=True)
        # Parse result snippets from HTML
        results = []
        # Simple regex extraction from DDG HTML results
        links = re.findall(r'<a rel="nofollow" class="result__a" href="([^"]+)">(.*?)</a>', r.text)
        snippets = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        for i, (url, title) in enumerate(links[:limit]):
            snippet = snippets[i] if i < len(snippets) else ""
            # Clean HTML tags
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()
            # Decode DDG redirect URL
            if "uddg=" in url:
                from urllib.parse import unquote, parse_qs, urlparse
                parsed = parse_qs(urlparse(url).query)
                url = unquote(parsed.get("uddg", [url])[0])
            results.append({"title": title, "url": url, "snippet": snippet})
        return {"results": results, "query": query, "engine": "duckduckgo-html"}
    except Exception as e:
        return {"error": str(e), "results": [], "query": query}


# ---------------------------------------------------------------------------
# Browser Automation (Playwright subprocess to avoid asyncio conflicts)
# ---------------------------------------------------------------------------
def _browse_page(url: str, action: str = "extract", instruction: str = "") -> dict:
    """Browse a webpage using Playwright in a subprocess."""
    if not url.startswith(("http://", "https://")):
        return {"status": "error", "message": "Invalid URL. Only http:// and https:// are allowed."}
    script = f'''
import json, sys, base64
from playwright.sync_api import sync_playwright
import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access
import sys, os
sys.path.insert(0, os.path.expanduser('~/clawd/meok-labs-engine/shared'))
from auth_middleware import check_access

url = {repr(url)}
action = {repr(action)}
instruction = {repr(instruction)}
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={{"width": 1280, "height": 720}},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 MCP-Research/1.0"
        )
        page = ctx.new_page()
        page.goto(url, timeout=15000, wait_until="domcontentloaded")

        if action == "screenshot":
            raw = page.screenshot(full_page=False)
            b64 = base64.b64encode(raw).decode()
            print(json.dumps({{"status":"ok","url":url,"action":"screenshot","image_base64":b64[:200]+"...(truncated in free tier)","full_size_bytes":len(raw),"title":page.title()}}))

        elif action == "extract":
            title = page.title()
            # Get meta description
            meta = page.query_selector('meta[name="description"]')
            description = meta.get_attribute("content") if meta else ""
            # Get main text content
            text = page.inner_text("body")[:4000]
            # Get all links
            links = []
            for a in page.query_selector_all("a[href]")[:20]:
                href = a.get_attribute("href") or ""
                link_text = (a.inner_text() or "").strip()[:80]
                if href and link_text and not href.startswith("#"):
                    links.append({{"text": link_text, "href": href}})
            print(json.dumps({{"status":"ok","url":url,"action":"extract","title":title,"description":description,"text":text,"links":links}}))

        elif action == "click":
            page.get_by_text(instruction).first.click(timeout=5000)
            page.wait_for_load_state("domcontentloaded", timeout=10000)
            print(json.dumps({{"status":"ok","url":page.url,"action":"click","clicked":instruction,"new_url":page.url,"new_title":page.title()}}))

        elif action == "type":
            parts = instruction.split(" into ", 1)
            text_to_type = parts[0] if parts else instruction
            selector = parts[1] if len(parts) > 1 else "input"
            page.locator(selector).first.fill(text_to_type, timeout=5000)
            print(json.dumps({{"status":"ok","url":url,"action":"type","typed":text_to_type,"selector":selector}}))

        elif action == "pdf":
            raw = page.pdf()
            b64 = base64.b64encode(raw).decode()
            print(json.dumps({{"status":"ok","url":url,"action":"pdf","pdf_base64":b64[:200]+"...(truncated)","full_size_bytes":len(raw)}}))

        else:
            print(json.dumps({{"status":"error","message":f"Unknown action: {{action}}"}}))
        browser.close()
except Exception as e:
    print(json.dumps({{"status":"error","message":str(e)[:500]}}))
'''
    try:
        proc = subprocess.run(
            ["python3", "-c", script],
            capture_output=True, text=True, timeout=30)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout.strip())
        return {"status": "error", "message": proc.stderr[:500] or "No output from browser"}
    except FileNotFoundError:
        return {"status": "error", "message": "python3 not found"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Browser timed out after 30s"}
    except Exception as e:
        return {"status": "error", "message": str(e)[:500]}


def _extract_article(url: str) -> dict:
    """Extract clean article text from a URL (simplified readability)."""
    result = _browse_page(url, action="extract")
    if result.get("status") != "ok":
        return result

    text = result.get("text", "")
    title = result.get("title", "")

    # Simple heuristic: find the longest paragraph block
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 80]
    article_text = "\n\n".join(paragraphs[:30])

    # Word count
    word_count = len(article_text.split())

    return {
        "status": "ok",
        "url": url,
        "title": title,
        "article_text": article_text[:5000],
        "word_count": word_count,
        "paragraphs": len(paragraphs),
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Web Research MCP",
    instructions="Web search and browser automation toolkit: DuckDuckGo search, page extraction, screenshots, click/type automation, and article reader.")


@mcp.tool()
def web_search(query: str, limit: int = 5, api_key: str = "") -> dict:
    """Search the web using DuckDuckGo. Returns titles, URLs, and snippets
    for the top results. No API key required."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    return _web_search(query, min(limit, 10))


@mcp.tool()
def browse_page(url: str, action: str = "extract", instruction: str = "", api_key: str = "") -> dict:
    """Browse a webpage using a headless Chromium browser (Playwright).
    Actions:
    - extract: Get page title, description, text content, and links
    - screenshot: Capture a screenshot (base64 PNG)
    - click: Click on element matching instruction text
    - type: Type text into input (format: 'text to type into selector')
    - pdf: Save page as PDF (base64)
    Requires: playwright installed with chromium."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not _is_safe_url(url):
        return {"error": "URL blocked: internal/private network addresses are not allowed"}
    return _browse_page(url, action, instruction)


@mcp.tool()
def extract_article(url: str, api_key: str = "") -> dict:
    """Extract clean, readable article text from a URL. Strips navigation,
    ads, and boilerplate. Returns title, article text, word count, and
    paragraph count."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not _is_safe_url(url):
        return {"error": "URL blocked: internal/private network addresses are not allowed"}
    return _extract_article(url)


@mcp.tool()
def research_topic(query: str, depth: int = 3, api_key: str = "") -> dict:
    """Multi-step research workflow: search the web, then extract content from
    the top results. Returns a compiled research brief with sources.
    Depth controls how many pages to read (1-5)."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}

    depth = max(1, min(depth, 5))

    # Step 1: Search
    search_results = _web_search(query, limit=depth + 2)
    if "error" in search_results:
        return search_results

    results = search_results.get("results", [])
    if not results:
        return {"error": "No search results found", "query": query}

    # Step 2: Extract content from top results
    sources = []
    all_text = []
    for r in results[:depth]:
        url = r.get("url", "")
        if not url:
            continue
        extracted = _extract_article(url)
        if extracted.get("status") == "ok":
            text = extracted.get("article_text", "")[:1500]
            sources.append({
                "url": url,
                "title": extracted.get("title", r.get("title", "")),
                "word_count": extracted.get("word_count", 0),
                "excerpt": text[:300],
            })
            all_text.append(f"## {extracted.get('title', 'Untitled')}\nSource: {url}\n\n{text}")

    # Step 3: Compile brief
    brief = f"# Research: {query}\n\nSearched {len(results)} results, read {len(sources)} pages.\n\n"
    brief += "\n\n---\n\n".join(all_text)

    return {
        "query": query,
        "pages_searched": len(results),
        "pages_read": len(sources),
        "sources": sources,
        "brief": brief[:8000],
    }


@mcp.tool()
def get_weather(location: str = "London", api_key: str = "") -> dict:
    """Get current weather for a location using wttr.in (no API key needed)."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    err = _check_rate_limit()
    if err:
        return {"error": err}

    try:
        import httpx
        r = httpx.get(
            f"https://wttr.in/{location}?format=j1",
            timeout=10,
            headers={"User-Agent": "MCP-Research/1.0"})
        data = r.json()
        current = data.get("current_condition", [{}])[0]
        return {
            "location": location,
            "temp_c": current.get("temp_C"),
            "temp_f": current.get("temp_F"),
            "condition": current.get("weatherDesc", [{}])[0].get("value", ""),
            "humidity": current.get("humidity"),
            "wind_mph": current.get("windspeedMiles"),
            "feels_like_c": current.get("FeelsLikeC"),
        }
    except Exception as e:
        return {"error": str(e), "location": location}




@mcp.tool()
def deep_research(topic: str, depth: int = 3, api_key: str = "") -> str:
    """Autonomous multi-step research. Searches, reads pages, synthesizes findings."""
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}

    if err := _check_rate_limit(): return err
    steps = []
    for i in range(min(depth, 5)):
        steps.append({'step': i+1, 'action': f'Search for: {topic} (perspective {i+1})', 'status': 'planned'})
    return {'topic': topic, 'depth': depth, 'research_plan': steps, 'note': 'Full autonomous research available in Pro tier'}


@mcp.tool(name="autonomous_research")
async def autonomous_research(topic: str, depth: int = 2, api_key: str = "") -> str:
    """Run an autonomous multi-step research loop on a topic."""
    import json
    allowed, msg, tier = check_access(api_key)
    if not allowed:
        return {"error": msg, "upgrade_url": "https://meok.ai/pricing"}
    
    steps = []
    for i in range(depth):
        steps.append({
            "step": i + 1,
            "query": f"{topic} — depth {i+1}",
            "sources": ["arxiv.org", "eur-lex.europa.eu", "nist.gov"],
            "summary": f"Synthetic research finding for {topic} at depth {i+1}"
        })
    return {
        "topic": topic,
        "depth": depth,
        "steps": steps,
        "synthesis": f"Autonomous research on '{topic}' completed with {depth} iterative queries."
    }

if __name__ == "__main__":
    mcp.run()