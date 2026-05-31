"""GCS object download and generation validation."""

from __future__ import annotations

import hashlib
import logging

from google.cloud import storage

logger = logging.getLogger(__name__)


def download_object(
    bucket_name: str, object_name: str, expected_generation: int
) -> tuple[bytes, str, int]:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.reload()
    actual_generation = blob.generation
    if int(actual_generation) != int(expected_generation):
        raise ValueError(
            f"Generation mismatch: expected {expected_generation}, "
            f"got {actual_generation}"
        )
    data = blob.download_as_bytes()
    content_hash = hashlib.sha256(data).hexdigest()
    return data, content_hash, int(actual_generation)
