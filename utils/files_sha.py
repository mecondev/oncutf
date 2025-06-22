import hashlib
from pathlib import Path

def calculate_sha256(file_path: Path) -> str:
    """
    Calculate the SHA-256 hash of a file.
    """
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def compare_folders(folder1: Path, folder2: Path) -> dict:
    """
    Compare two folders and return a dictionary of file names and their SHA-256 hashes.
    """
    result = {}
    for file1 in folder1.glob("*"):
        file2 = folder2 / file1.name
        if file2.exists():
            sha1 = calculate_sha256(file1)
            sha2 = calculate_sha256(file2)
            result[file1.name] = (sha1 == sha2, sha1, sha2)
    return result
