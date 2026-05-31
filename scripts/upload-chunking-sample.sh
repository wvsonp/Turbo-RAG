#!/usr/bin/env bash
# Upload a multi-paragraph sample document for chunking experiments (2.4).
set -euo pipefail

PROJECT="${GCP_PROJECT:-turbo-rag}"
BUCKET="${INGESTION_BUCKET:-rag-ingestion-dev}"
OBJECT="${1:-experiments/chunking-sample.txt}"
DEST="gs://${BUCKET}/${OBJECT}"

cat > /tmp/chunking-sample.txt <<'EOF'
Introduction to retrieval-augmented generation.

Retrieval-augmented generation combines a language model with an external knowledge base.
The system retrieves relevant documents before generating an answer.
Good chunking improves recall and keeps context windows manageable.

Chunking strategies vary in how they split source text.
Fixed-size chunking splits text at character boundaries with overlap.
Recursive chunking prefers paragraph, line, and sentence boundaries before falling back to words.
Semantic chunking groups sentences when embedding similarity drops between adjacent sentences.

Experiments should use the same source document for all strategies.
Metrics include chunk count, average chunk length, and embedding batch count.
EOF

gcloud storage cp /tmp/chunking-sample.txt "$DEST" --project="$PROJECT"
echo "Uploaded ${DEST}"
gcloud storage ls -L "$DEST" --project="$PROJECT" | head -20
