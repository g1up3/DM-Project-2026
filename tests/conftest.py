"""Rende importabili i moduli dell'harness (benchmark/ non e' un package)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "benchmark"))
