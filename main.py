"""Compatibility entry point; the backend app is defined in backend/app/main.py."""

from pathlib import Path
import sys

backend_path = str(Path(__file__).resolve().parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app