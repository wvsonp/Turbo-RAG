FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY main.py .
USER appuser
ENV SERVICE_NAME=api
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
