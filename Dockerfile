FROM python:3.12-slim

WORKDIR /app

RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webscrape_mcp.py .

ENV HOST=0.0.0.0

EXPOSE 8000

CMD ["python", "webscrape_mcp.py", "streamable-http"]
