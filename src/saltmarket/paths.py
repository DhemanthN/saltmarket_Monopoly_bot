"""Where outputs are written. SALTMARKET_OUTPUT redirects them, for example in quick runs."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("SALTMARKET_OUTPUT", ROOT))
RESULTS = OUTPUT / "results"
FIGURES = RESULTS / "figures"
MODELS = OUTPUT / "models"
CHECKPOINTS = OUTPUT / "checkpoints"
