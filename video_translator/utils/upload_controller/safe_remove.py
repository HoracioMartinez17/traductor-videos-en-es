import os

def safe_remove(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)
