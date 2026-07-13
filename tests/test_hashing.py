import hashlib

from app.services.hashing import hash_bytes, hash_file


def test_hash_file_matches_hashlib(tmp_path):
    content = b"FIR/0042/2026 evidence contents for hashing test"
    file_path = tmp_path / "evidence.txt"
    file_path.write_bytes(content)

    sha256_hex, md5_hex = hash_file(file_path)

    assert sha256_hex == hashlib.sha256(content).hexdigest()
    assert md5_hex == hashlib.md5(content).hexdigest()


def test_hash_file_streams_large_content(tmp_path):
    content = b"x" * (3 * 1024 * 1024 + 17)  # spans multiple CHUNK_SIZE reads
    file_path = tmp_path / "large.bin"
    file_path.write_bytes(content)

    sha256_hex, md5_hex = hash_file(file_path)

    assert sha256_hex == hashlib.sha256(content).hexdigest()
    assert md5_hex == hashlib.md5(content).hexdigest()


def test_hash_bytes():
    content = b"in-memory content"
    sha256_hex, md5_hex = hash_bytes(content)
    assert sha256_hex == hashlib.sha256(content).hexdigest()
    assert md5_hex == hashlib.md5(content).hexdigest()
