# WebScrape MCP Server

Un servidor MCP (Model Context Protocol) que permite a agentes de IA buscar en la web y extraer contenido limpio en Markdown.

## Tools

| Tool | Descripción |
|------|-------------|
| `webscrape_search` | Busca en la web (DuckDuckGo) y scrapea los resultados |
| `webscrape_fetch_url` | Obtiene una URL y la convierte a Markdown limpio |
| `webscrape_batch_fetch` | Obtiene hasta 5 URLs en paralelo |

## Cómo usarlo

### Opción 1 — MCPize (recomendada)

1. Ve a https://mcpize.com/marketplace
2. Busca **Web Scrape** y haz clic en **Start Free**
3. Obtendrás una API key
4. Configura en tu IA cliente:

```json
{
  "mcpServers": {
    "webscrape": {
      "url": "https://webscrape.mcpize.run",
      "headers": {
        "Authorization": "Bearer tu-api-key"
      }
    }
  }
}
```

### Opción 2 — Render (developer)

```json
{
  "mcpServers": {
    "webscrape": {
      "url": "https://webscrape-mcp.onrender.com"
    }
  }
}
```

### Opción 3 — Local

```bash
git clone https://github.com/carrasquelalex1/webscrape-mcp.git
cd webscrape-mcp
pip install -r requirements.txt
python webscrape_mcp.py
```

## Stack

- Python + FastMCP
- httpx + BeautifulSoup4 + markdownify
- DuckDuckGo search (ddgs)
- Hosteado en Render y MCPize

## Registro Oficial

`io.github.carrasquelalex1/webscrape-mcp`

## Licencia

MIT
