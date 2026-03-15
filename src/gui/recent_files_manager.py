import os

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu


class RecentFilesManager(QObject):
    """Manages the Recent Files menu and persistence via QSettings."""

    file_selected = pyqtSignal(str)

    def __init__(self, parent: QObject, max_count: int = 5):
        super().__init__(parent)
        self._menu: QMenu | None = None
        self._max_count = max_count
        self._recent_files: list[str] = []
        self._load()

    def set_menu(self, menu: QMenu) -> None:
        """Bind to a QMenu and populate it."""
        self._menu = menu
        self._update_menu()

    def add(self, path: str) -> None:
        """Add a path to the top of the recent files list."""
        abs_path = os.path.abspath(path)
        if abs_path in self._recent_files:
            self._recent_files.remove(abs_path)
        self._recent_files.insert(0, abs_path)
        self._recent_files = self._recent_files[:self._max_count]
        self._save()
        self._update_menu()

    def remove(self, path: str) -> None:
        """Remove a path from the recent files list."""
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._save()
        self._update_menu()

    def clear(self) -> None:
        """Clear all recent files."""
        self._recent_files = []
        self._save()
        self._update_menu()

    def _load(self) -> None:
        settings = QSettings()
        paths = settings.value("recentFiles", defaultValue=[], type=list) or []
        self._recent_files = [p for p in paths if isinstance(p, str)]

    def _save(self) -> None:
        settings = QSettings()
        settings.setValue("recentFiles", self._recent_files)

    def _update_menu(self) -> None:
        if self._menu is None:
            return
        self._menu.clear()
        if not self._recent_files:
            no_action = QAction("(No recent files)", self)
            no_action.setEnabled(False)
            self._menu.addAction(no_action)
            return
        for path in self._recent_files:
            parent = os.path.basename(os.path.dirname(path))
            name = f"{parent}/{os.path.basename(path)}" if parent else os.path.basename(path)
            action = QAction(name, self)
            action.setToolTip(path)
            action.setStatusTip(path)
            action.triggered.connect(lambda checked, p=path: self.file_selected.emit(p))
            self._menu.addAction(action)
        self._menu.addSeparator()
        clear_action = QAction("Clear Recent Files", self)
        clear_action.triggered.connect(self.clear)
        self._menu.addAction(clear_action)
