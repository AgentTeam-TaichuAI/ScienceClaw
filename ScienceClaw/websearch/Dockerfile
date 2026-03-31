FROM python:3.12-slim

WORKDIR /search

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python dependencies
RUN pip install \
    "crawl4ai" \
    fastapi \
    "uvicorn[standard]" \
    gunicorn \
    aiohttp \
    pydantic \
    python-dotenv \
    markdown \
    beautifulsoup4

# Install Playwright Chromium browser + system deps
RUN python -m playwright install --with-deps chromium

# Copy websearch source code
COPY . /search/

EXPOSE 8068

CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8068", "--timeout", "120"]
