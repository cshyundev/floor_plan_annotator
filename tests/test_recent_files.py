"""Tests for FEAT-007: Recent Files logic in MainWindow.

Uses SimpleNamespace stubs to avoid Qt widget instantiation.
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

from src.gui.main_window import MainWindow


def _make_stub() -> SimpleNamespace:
    """Create a minimal stub that binds MainWindow recent-files methods."""
    stub = SimpleNamespace()
    stub._recent_files = []
    stub._recent_files_menu = MagicMock()
    stub.statusBar = lambda: MagicMock()

    # Bind methods under test
    stub._save_recent_files = MainWindow._save_recent_files.__get__(stub)
    stub._add_to_recent_files = MainWindow._add_to_recent_files.__get__(stub)
    stub._update_recent_files_menu = MainWindow._update_recent_files_menu.__get__(stub)
    stub._clear_recent_files = MainWindow._clear_recent_files.__get__(stub)
    stub._load_recent_files = MainWindow._load_recent_files.__get__(stub)

    return stub


class TestAddToRecentFiles(unittest.TestCase):
    def setUp(self):
        self.stub = _make_stub()

    @patch("src.gui.main_window.MainWindow._save_recent_files")
    @patch("src.gui.main_window.MainWindow._update_recent_files_menu")
    def _call_add(self, path, mock_update, mock_save):
        # Directly mutate state to avoid Qt calls in helpers
        self.stub._save_recent_files = mock_save.__get__(self.stub)
        self.stub._update_recent_files_menu = mock_update.__get__(self.stub)
        self.stub._add_to_recent_files(path)

    def test_new_path_appears_at_front(self):
        with patch.object(self.stub, "_save_recent_files"), \
             patch.object(self.stub, "_update_recent_files_menu"):
            self.stub._add_to_recent_files("/a/b/c.json")
        self.assertEqual(self.stub._recent_files[0], os.path.abspath("/a/b/c.json"))

    def test_duplicate_moves_to_front(self):
        self.stub._recent_files = ["/a.json", "/b.json"]
        with patch.object(self.stub, "_save_recent_files"), \
             patch.object(self.stub, "_update_recent_files_menu"):
            self.stub._add_to_recent_files("/b.json")
        self.assertEqual(self.stub._recent_files, ["/b.json", "/a.json"])

    def test_list_trimmed_to_five(self):
        with patch.object(self.stub, "_save_recent_files"), \
             patch.object(self.stub, "_update_recent_files_menu"):
            for i in range(6):
                self.stub._add_to_recent_files(f"/path{i}.json")
        self.assertEqual(len(self.stub._recent_files), 5)
        self.assertEqual(self.stub._recent_files[0], os.path.abspath("/path5.json"))

    def test_abs_path_normalisation(self):
        with patch.object(self.stub, "_save_recent_files"), \
             patch.object(self.stub, "_update_recent_files_menu"):
            self.stub._add_to_recent_files("relative/path.json")
        stored = self.stub._recent_files[0]
        self.assertTrue(os.path.isabs(stored))
        self.assertEqual(stored, os.path.abspath("relative/path.json"))


class TestClearRecentFiles(unittest.TestCase):
    def test_clear_empties_list(self):
        stub = _make_stub()
        stub._recent_files = ["/a.json", "/b.json"]
        with patch.object(stub, "_save_recent_files"), \
             patch.object(stub, "_update_recent_files_menu"):
            stub._clear_recent_files()
        self.assertEqual(stub._recent_files, [])


class TestOpenRecentFile(unittest.TestCase):
    def setUp(self):
        self.stub = _make_stub()
        self.stub._confirm_discard_changes = MagicMock(return_value=True)
        self.stub.load_data = MagicMock()
        self.stub._open_recent_file = MainWindow._open_recent_file.__get__(self.stub)
        self.stub._status_msg = None
        status_bar = MagicMock()
        status_bar.showMessage = lambda msg, timeout=0: setattr(self.stub, "_status_msg", msg)
        self.stub.statusBar = lambda: status_bar

    def test_nonexistent_file_removed_from_list(self):
        path = "/nonexistent/path.json"
        self.stub._recent_files = [path]
        with patch.object(self.stub, "_save_recent_files"), \
             patch.object(self.stub, "_update_recent_files_menu"), \
             patch("os.path.exists", return_value=False):
            self.stub._open_recent_file(path)
        self.assertNotIn(path, self.stub._recent_files)

    def test_nonexistent_file_shows_status_message(self):
        path = "/nonexistent/path.json"
        self.stub._recent_files = [path]
        with patch.object(self.stub, "_save_recent_files"), \
             patch.object(self.stub, "_update_recent_files_menu"), \
             patch("os.path.exists", return_value=False):
            self.stub._open_recent_file(path)
        self.assertIsNotNone(self.stub._status_msg)
        self.assertIn("path.json", self.stub._status_msg)

    def test_existing_file_calls_load_data(self):
        path = "/exists/model.ply"
        self.stub._recent_files = [path]
        with patch("os.path.exists", return_value=True):
            self.stub._open_recent_file(path)
        self.stub.load_data.assert_called_once_with(path)

    def test_discard_changes_cancelled_skips_load(self):
        path = "/exists/model.ply"
        self.stub._recent_files = [path]
        self.stub._confirm_discard_changes.return_value = False
        with patch("os.path.exists", return_value=True):
            self.stub._open_recent_file(path)
        self.stub.load_data.assert_not_called()


class TestLoadSaveRecentFilesQSettings(unittest.TestCase):
    def test_load_recent_files_from_settings(self):
        stub = _make_stub()
        expected = ["/a.json", "/b.json"]
        with patch("PyQt6.QtCore.QSettings") as MockQSettings:
            instance = MockQSettings.return_value
            instance.value.return_value = expected
            stub._load_recent_files()
        self.assertEqual(stub._recent_files, expected)

    def test_save_recent_files_to_settings(self):
        stub = _make_stub()
        stub._recent_files = ["/x.json"]
        with patch("PyQt6.QtCore.QSettings") as MockQSettings:
            instance = MockQSettings.return_value
            stub._save_recent_files()
            instance.setValue.assert_called_once_with("recentFiles", ["/x.json"])

    def test_load_handles_missing_key(self):
        stub = _make_stub()
        with patch("PyQt6.QtCore.QSettings") as MockQSettings:
            instance = MockQSettings.return_value
            instance.value.return_value = None
            stub._load_recent_files()
        self.assertEqual(stub._recent_files, [])


if __name__ == "__main__":
    unittest.main()
