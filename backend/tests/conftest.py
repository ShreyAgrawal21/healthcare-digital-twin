import sys
from pathlib import Path

# Ensure the backend directory is importable when pytest
# collects tests from the tests/ directory.
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
