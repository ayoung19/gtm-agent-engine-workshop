import sys
from pathlib import Path

# Make the repo root importable so `gtm_agent` resolves however pytest is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
