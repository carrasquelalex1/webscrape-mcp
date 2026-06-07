# WebScrape MCP Server

English · [Español](#español)

---

## English

MCP server that lets AI agents search the web and extract clean Markdown content — no ads, no clutter, just the text your LLM needs.

### Tools

| Tool | Description |
|------|-------------|
| `webscrape_search` | Search the web (DuckDuckGo) and scrape results into Markdown |
| `webscrape_fetch_url` | Fetch a single URL and return clean Markdown. Supports `use_readability` for article extraction and auto-detects PDFs |
| `webscrape_batch_fetch` | Fetch up to 5 URLs in parallel. Supports PDF auto-detection |

### Features

- **PDF support**: URLs ending in `.pdf` or with `application/pdf` content-type are auto-detected and text is extracted page by page
- **Readability mode**: Pass `use_readability=True` to `webscrape_fetch_url` for cleaner article extraction using Mozilla Readability (removes nav, sidebars, ads, comments)
- **DuckDuckGo search**: No API key required, just a search query
- **Built-in cache**: 200-entry cache with automatic eviction for repeated URLs
- **Batch fetching**: Up to 5 URLs in parallel

### How to use

#### Option 1 — MCPize (recommended)

1. Go to https://mcpize.com/marketplace
2. Search **Web Scrape** and click **Start Free**
3. You'll get an API key
4. Configure in your AI client:

```json
{
  "mcpServers": {
    "webscrape": {
      "url": "https://webscrape.mcpize.run",
      "headers": {
        "Authorization": "Bearer your-api-key"
      }
    }
  }
}
```

#### Option 2 — Render (dev)

```json
{
  "mcpServers": {
    "webscrape": {
      "url": "https://webscrape-mcp.onrender.com"
    }
  }
}
```

#### Option 3 — Local

```bash
git clone https://github.com/carrasquelalex1/webscrape-mcp.git
cd webscrape-mcp
pip install -r requirements.txt
python webscrape_mcp.py
```

### Official Registry

`io.github.carrasquelalex1/webscrape-mcp`

### Dependencies

`mcp`, `httpx`, `beautifulsoup4`, `markdownify`, `pydantic`, `ddgs`, `readability-lxml`, `PyMuPDF`

### License

MIT

---

## Español

Servidor MCP que permite a agentes de IA buscar en la web y extraer contenido limpio en Markdown — sin anuncios, sin navegación, solo el texto que tu LLM necesita.

### Tools

| Tool | Descripción |
|------|-------------|
| `webscrape_search` | Busca en la web (DuckDuckGo) y extrae los resultados a Markdown |
| `webscrape_fetch_url` | Obtiene una URL y la convierte a Markdown limpio. Soporta `use_readability` para extracción de artículos y detecta PDFs automáticamente |
| `webscrape_batch_fetch` | Obtiene hasta 5 URLs en paralelo. Soporta detección automática de PDFs |

### Características

- **Soporte PDF**: URLs que terminan en `.pdf` o con content-type `application/pdf` se detectan automáticamente y se extrae el texto página por página
- **Modo Readability**: Usá `use_readability=True` en `webscrape_fetch_url` para extraer artículos de forma más limpia (elimina navegación, barras laterales, anuncios, comentarios)
- **Búsqueda DuckDuckGo**: Sin necesidad de API key
- **Caché integrada**: 200 entradas con evicción automática para URLs repetidas
- **Batch fetching**: Hasta 5 URLs en paralelo

### Cómo usarlo

#### Opción 1 — MCPize (recomendada)

1. Ve a https://mcpize.com/marketplace
2. Busca **Web Scrape** y haz clic en **Start Free**
3. Obtendrás una API key
4. Configura en tu cliente de IA:

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

#### Opción 2 — Render (desarrollo)

```json
{
  "mcpServers": {
    "webscrape": {
      "url": "https://webscrape-mcp.onrender.com"
    }
  }
}
```

#### Opción 3 — Local

```bash
git clone https://github.com/carrasquelalex1/webscrape-mcp.git
cd webscrape-mcp
pip install -r requirements.txt
python webscrape_mcp.py
```

### Registro Oficial

`io.github.carrasquelalex1/webscrape-mcp`

### Dependencias

`mcp`, `httpx`, `beautifulsoup4`, `markdownify`, `pydantic`, `ddgs`, `readability-lxml`, `PyMuPDF`

### Licencia

MIT
