#!/usr/bin/env python3
"""Sliding Puzzle Game.

Usage::

    uv run main.py cli            # Terminal (ANSI)
    uv run main.py gui            # PyQt GUI (default)
    uv run main.py gui:pyqt       # PyQt GUI
    uv run main.py gui:pygame     # Pygame GUI
"""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # python/
PROJECT_ROOT = ROOT.parent  # sliding-game/
DATA_DIR = PROJECT_ROOT / "data"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# -- target registry ----------------------------------------------------------

_TARGETS: dict[str, str] = {
    "cli": "frontend.cli.vanilla.app",
    "gui": "frontend.gui.pyqt.app",
    "gui:pyqt": "frontend.gui.pyqt.app",
    "gui:pygame": "frontend.gui.pygame.app",
}


# -- entry point --------------------------------------------------------------


def main() -> None:
    """Launch the requested frontend."""
    target = sys.argv[1] if len(sys.argv) > 1 else ""

    if target not in _TARGETS:
        print()
        print("  Usage:  uv run main.py <target>")
        print()
        print("  Targets:")
        for key in _TARGETS:
            note = ""
            if key == "gui":
                note = "  (default: pyqt)"
            print(f"    {key:<16}{note}")
        print()
        sys.exit(1)

    mod = importlib.import_module(_TARGETS[target])
    mod.run(data_dir=DATA_DIR)


if __name__ == "__main__":
    main()
