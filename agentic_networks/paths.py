"""Canonical locations of the repository's data directories.

Every module resolves data paths through this one anchor rather than off its own
``__file__``. That keeps the paths correct no matter where a script lives, so moving
an entry point between directories cannot silently point it at a non-existent
``topologies/`` or ``logs/`` (a failure that surfaces at run time, not import time).

``PROJECT_ROOT`` is the repository checkout: this file is ``<root>/agentic_networks/paths.py``,
so the root is two levels up. An editable install (``pip install -e .``) leaves the package
inside the checkout, so this holds there too.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ASSETS_DIR = PROJECT_ROOT / "assets"
EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"
LOGS_DIR = PROJECT_ROOT / "logs"
POLICIES_DIR = PROJECT_ROOT / "policies"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TOPOLOGIES_DIR = PROJECT_ROOT / "topologies"
TOOLS_DIR = PROJECT_ROOT / "tools"
