"""Allow tests run from the repository root to import Backend modules."""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "Backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
