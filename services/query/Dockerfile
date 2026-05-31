FROM python:3.11-slim AS builder
WORKDIR /app
COPY query/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY query/main.py query/models.py query/retrieval.py ./
COPY shared/rag_platform /app/rag_platform
ENV PYTHONPATH=/app
USER appuser
ENV SERVICE_NAME=query
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
