import os
import sys

# Ensure root directory is in sys.path so backend modules resolve properly
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.main import app

# Vercel entrypoint
handler = app

