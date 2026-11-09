"""Repository locations shared by data, models and interface components."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'data'
ARTIFACTS_DIR = ROOT / 'artifacts'
ARTIFACT_DIR = ARTIFACTS_DIR / 'chatbot'
ASSETS_DIR = ROOT / 'assets'
