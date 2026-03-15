"""Entry point for the map alignment tool.

Usage:
    python -m src.map_align
"""

import sys
import os

# Add repo root to path so we can import from src/
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from PyQt6.QtWidgets import QApplication

from src.core.config import apply_theme
from src.map_align.app import AlignmentWindow


def main() -> None:
    """Launch the Map Alignment Tool as a standalone PyQt6 application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Map Alignment Tool")
    apply_theme(app)

    window = AlignmentWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
