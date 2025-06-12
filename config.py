# config.py
import os

# Cache configuration
CACHE_DIR = "/opt/render/.cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR, exist_ok=True)