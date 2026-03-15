import os

from PyQt6.QtCore import QObject, QSettings, QTimer


class AutosaveManager(QObject):
    """Manages periodic autosaving of project data."""

    def __init__(self, parent: QObject, get_save_data: callable, get_file_path: callable,
                 is_dirty: callable):
        super().__init__(parent)
        self._get_save_data = get_save_data
        self._get_file_path = get_file_path
        self._is_dirty = is_dirty
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.do_autosave)
        self.load_settings()

    def load_settings(self) -> None:
        """Load autosave enabled/interval from QSettings."""
        s = QSettings()
        enabled = s.value("autosave/enabled", defaultValue=True, type=bool)
        interval_ms = s.value("autosave/interval_minutes", defaultValue=5, type=int) * 60 * 1000
        self._timer.setInterval(interval_ms)
        if enabled:
            self._timer.start()
        else:
            self._timer.stop()

    def autosave_path(self) -> str | None:
        """Return the autosave file path, or None if no project file is set."""
        file_path = self._get_file_path()
        if not file_path:
            return None
        folder = os.path.dirname(file_path)
        name = os.path.basename(file_path)
        return os.path.join(folder, f".{name}.autosave.json")

    def do_autosave(self) -> None:
        """Perform an autosave if the project is dirty."""
        if not self._get_file_path():
            return
        if not self._is_dirty():
            return
        path = self.autosave_path()
        if path is None:
            return
        from src.core.io import ProjectIO
        try:
            project_data = self._get_save_data()
            ProjectIO.save_project(project_data, path)
        except Exception:
            pass

    def delete_autosave(self) -> None:
        """Delete the autosave file if it exists."""
        path = self.autosave_path()
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
