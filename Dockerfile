# -- Stage 1: builder
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

# Install to /install so we can copy cleanly to runtime
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --Stage 2: runtime
FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy packages to system Python (no user/permission issues)
COPY --from=builder /install /usr/local

WORKDIR /app

COPY src/ ./src/
COPY api.py .
COPY .env .
COPY data/chroma_db/ ./data/chroma_db/

RUN useradd -m -u 1000 regiq && chown -R regiq:regiq /app
USER regiq

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]