import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def hash_file(path: str | Path) -> tuple[str, str]:
    """Stream a file once and return (sha256_hex, md5_hex).

    Streaming avoids loading large forensic extractions fully into memory,
    and computing both digests in a single pass avoids reading the file twice.
    """
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
            md5.update(chunk)
    return sha256.hexdigest(), md5.hexdigest()


def hash_bytes(data: bytes) -> tuple[str, str]:
    return hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest()
