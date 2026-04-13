# Web Research MCP Server

> **By [MEOK AI Labs](https://meok.ai)** — Sovereign AI tools for everyone.

Web search and browser automation toolkit for AI agents. Search the web via DuckDuckGo (no API key), browse pages with headless Chromium, extract article content, take screenshots, and run multi-step research workflows.

[![MCPize](https://img.shields.io/badge/MCPize-Listed-blue)](https://mcpize.com/mcp/web-research)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-255+_servers-purple)](https://meok.ai)

## Tools

| Tool | Description |
|------|-------------|
| `web_search` | Search the web using DuckDuckGo (no API key needed) |
| `browse_page` | Browse a webpage using headless Chromium (Playwright) |
| `extract_article` | Extract clean, readable article text from a URL |
| `research_topic` | Multi-step research: search the web, then extract content |
| `get_weather` | Get current weather for a location via wttr.in |

## Quick Start

```bash
pip install mcp
git clone https://github.com/CSOAI-ORG/web-research-mcp.git
cd web-research-mcp
python server.py
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "web-research": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/web-research-mcp"
    }
  }
}
```

## Pricing

| Plan | Price | Requests |
|------|-------|----------|
| Free | $0/mo | 25 calls/day |
| Pro | $9/mo | Unlimited + full screenshots + PDF export |
| Enterprise | Contact us | Custom + proxy rotation + CAPTCHA solving |

[Get on MCPize](https://mcpize.com/mcp/web-research)

## Part of MEOK AI Labs

This is one of 255+ MCP servers by MEOK AI Labs. Browse all at [meok.ai](https://meok.ai) or [GitHub](https://github.com/CSOAI-ORG).

---
**MEOK AI Labs** | [meok.ai](https://meok.ai) | nicholas@meok.ai | United Kingdom
