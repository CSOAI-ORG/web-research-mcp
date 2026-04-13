> **By [MEOK AI Labs](https://meok.ai)** — Sovereign AI tools for everyone.

# Web Research MCP Server

Web search and browser automation toolkit for AI agents. Search the web via DuckDuckGo (no API key), browse pages with headless Chromium, extract article content, take screenshots, interact with forms, and run multi-step research workflows that search and read multiple pages automatically.

## Tools

| Tool | Description |
|------|-------------|
| `web_search` | DuckDuckGo search -- no API key required |
| `browse_page` | Full browser automation: extract, screenshot, click, type, PDF |
| `extract_article` | Clean article extraction (strips nav/ads/boilerplate) |
| `research_topic` | Multi-step workflow: search + read top N pages + compile brief |
| `get_weather` | Current weather for any location (wttr.in) |

## Installation

```bash
pip install mcp httpx playwright duckduckgo-search
python -m playwright install chromium
```

The `duckduckgo-search` package is optional -- the server falls back to HTML scraping if not installed. Playwright + Chromium is required for browse_page, extract_article, and research_topic.

## Usage

### Run the server

```bash
python server.py
```

### Claude Desktop config

```json
{
  "mcpServers": {
    "web-research": {
      "command": "python",
      "args": ["/path/to/web-research-mcp/server.py"]
    }
  }
}
```

### Example calls

**Web search:**
```
Tool: web_search
Input: {"query": "best practices for MCP server development", "limit": 5}
Output: {"results": [{"title": "...", "url": "...", "snippet": "..."}], "query": "...", "engine": "duckduckgo"}
```

**Browse and extract page:**
```
Tool: browse_page
Input: {"url": "https://example.com/article", "action": "extract"}
Output: {"status": "ok", "title": "...", "text": "...", "links": [...]}
```

**Take screenshot:**
```
Tool: browse_page
Input: {"url": "https://example.com", "action": "screenshot"}
Output: {"status": "ok", "image_base64": "...", "full_size_bytes": 142531}
```

**Research a topic (automated):**
```
Tool: research_topic
Input: {"query": "MCP protocol specification 2026", "depth": 3}
Output: {"pages_searched": 5, "pages_read": 3, "sources": [...], "brief": "# Research: ..."}
```

## Pricing

| Tier | Limit | Price |
|------|-------|-------|
| Free | 25 calls/day | $0 |
| Pro | Unlimited + full screenshots + PDF export | $9/mo |
| Enterprise | Custom + proxy rotation + CAPTCHA solving | Contact us |

## License

MIT
