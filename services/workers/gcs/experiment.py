"""Download test documents for chunking experiments (no generation guard)."""

from __future__ import annotations

import hashlib
import re

from google.cloud import storage

_GCS_URI = re.compile(r"^gs://([^/]+)/(.+)$")


def parse_gcs_uri(uri: str) -> tuple[str, str]:
    match = _GCS_URI.match(uri.strip())
    if not match:
        raise ValueError(f"Invalid GCS URI: {uri!r}")
    return match.group(1), match.group(2)


def download_uri(uri: str) -> tuple[str, str, int, bytes, str]:
    bucket_name, object_name = parse_gcs_uri(uri)
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(object_name)
    blob.reload()
    data = blob.download_as_bytes()
    content_hash = hashlib.sha256(data).hexdigest()
    return bucket_name, object_name, int(blob.generation), data, content_hash
