import os

def cleanup_temp_files(*paths):
    for path in paths:
        if path and os.path.exists(path):
            os.remove(path)
