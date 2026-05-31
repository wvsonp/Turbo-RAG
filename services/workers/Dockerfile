FROM python:3.11-slim AS builder
WORKDIR /app
COPY workers/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/prefect /usr/local/bin/prefect
COPY workers/main.py ./
COPY workers/flows /app/flows
COPY workers/db /app/db
COPY workers/chunking /app/chunking
COPY workers/experiments /app/experiments
COPY workers/parsing /app/parsing
COPY workers/embedding /app/embedding
COPY workers/qdrant /app/qdrant
COPY workers/gcs /app/gcs
COPY workers/migrations /app/migrations
COPY workers/prefect.yaml /app/prefect.yaml
COPY shared/rag_platform /app/rag_platform
ENV PYTHONPATH=/app
USER appuser
ENV SERVICE_NAME=workers
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
