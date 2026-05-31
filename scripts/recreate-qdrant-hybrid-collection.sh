#!/usr/bin/env bash
# Drop the dev Qdrant collection so ingestion recreates dense+sparse data after
# schema or sparse encoder changes (3.2).
set -euo pipefail

QDRANT_URL="${QDRANT_URL:-http://qdrant.platform.svc.cluster.local:6333}"
COLLECTION="${QDRANT_COLLECTION:-rag_chunks_dev}"

echo "Deleting collection ${COLLECTION} at ${QDRANT_URL} ..."
curl -sf -X DELETE "${QDRANT_URL}/collections/${COLLECTION}"
echo
echo "Collection deleted. Re-upload documents to trigger ingestion, then query via POST /query."
