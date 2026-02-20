import os
from typing import Optional

def safe_remove(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        os.remove(path)
