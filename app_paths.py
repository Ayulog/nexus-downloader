"""Writable application paths and bundled read-only resources."""
import sys
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else TEMPLATE_DIR
