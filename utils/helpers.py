import os

def ensure_uploads_dir(path: str = 'uploads'):
    os.makedirs(path, exist_ok=True)
    return path

# Add other helper functions as needed
