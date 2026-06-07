# Deploy: WebScrape MCP Server

## Opción 1: MCPize (recomendada — hosting + marketplace + cobros)

```bash
# 1. Instalar CLI de MCPize
npm install -g @mcpize/cli

# 2. Ir al directorio
cd /tmp/opencode/webscrape-mcp

# 3. Desplegar
mcpize deploy

# 4. Publicar en marketplace
mcpize publish
```

MCPize te da hosting, marketplace y pagos vía Stripe.
Tú ganas 80% de cada venta (85% si activas antes del 10-jun-2026).

---

## Opción 2: Auto-hosting (tu máquina, i3-2120)

### Con Docker:
```bash
docker build -t webscrape-mcp .
docker run -d --name webscrape-mcp -p 8000:8000 webscrape-mcp
```

### Sin Docker (directo):
```bash
cd /tmp/opencode/webscrape-mcp
./venv/bin/python webscrape_mcp.py
```

El servidor arranca en `http://localhost:8000` con transporte streamable HTTP.

### Exponer a internet (para venderlo):
1. Abrir puerto 8000 en router (NAT forwarding)
2. Usar DDNS (no-ip, duckdns) si tu IP es dinámica
3. O mejor: túnel Cloudflare (`cloudflared tunnel --url http://localhost:8000`)
4. O: desplegar en VPS $5/mes (DigitalOcean, Hetzner) y tu i3-2120 no paga nada

---

## Opción 3: Registro Oficial MCP (gratis, visibilidad)

```bash
# Instalar publisher CLI
npx @modelcontextprotocol/publisher-cli

# Publicar en registry.modelcontextprotocol.io
mcp-publisher publish \
  --namespace io.github.tuusuario \
  --name webscrape-mcp \
  --url https://tu-dominio.com/mcp
```

Esto hace que aparezcas automáticamente en PulseMCP (7 días).

---

## Stack completo

```
webscrape-mcp/
├── webscrape_mcp.py    # El servidor MCP (2 tools)
├── requirements.txt    # Dependencias Python
├── Dockerfile          # Para deploy containerizado
└── mcpize.yaml         # Config para MCPize marketplace
```

## Tools incluidas

| Tool | Descripción |
|------|-------------|
| `webscrape_fetch_url` | Fetch 1 URL → Markdown limpio |
| `webscrape_batch_fetch` | Fetch hasta 5 URLs en paralelo |
