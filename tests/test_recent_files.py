"""Tests for FEAT-007: Recent Files logic via RecentFilesManager.

Uses RecentFilesManager directly with mocked QSettings.
"""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.gui.recent_files_manager import RecentFilesManager
from src.gui.main_window import MainWindow


def _make_manager() -> RecentFilesManager:
    """Create a RecentFilesManager with QSettings mocked to return empty list."""
    with patch("src.gui.recent_files_manager.QSettings") as MockQSettings:
        instance = MockQSettings.return_value
        instance.value.return_value = []
        mgr = RecentFilesManager(parent=None)
    return mgr


class TestAddToRecentFiles(unittest.TestCase):
    def setUp(self):
        self.mgr = _make_manager()

    def test_new_path_appears_at_front(self):
        with patch("src.gui.recent_files_manager.QSettings"):
            self.mgr.add("/a/b/c.json")
        self.assertEqual(self.mgr._recent_files[0], os.path.abspath("/a/b/c.json"))

    def test_duplicate_moves_to_front(self):
        self.mgr._recent_files = ["/a.json", "/b.json"]
        with patch("src.gui.recent_files_manager.QSettings"):
            self.mgr.add("/b.json")
        self.assertEqual(self.mgr._recent_files, ["/b.json", "/a.json"])

    def test_list_trimmed_to_five(self):
        with patch("src.gui.recent_files_manager.QSettings"):
            for i in range(6):
                self.mgr.add(f"/path{i}.json")
        self.assertEqual(len(self.mgr._recent_files), 5)
        self.assertEqual(self.mgr._recent_files[0], os.path.abspath("/path5.json"))

    def test_abs_path_normalisation(self):
        with patch("src.gui.recent_files_manager.QSettings"):
            self.mgr.add("relative/path.json")
        stored = self.mgr._recent_files[0]
        self.assertTrue(os.path.isabs(stored))
        self.assertEqual(stored, os.path.abspath("relative/path.json"))


class TestClearRecentFiles(unittest.TestCase):
    def test_clear_empties_list(self):
        mgr = _make_manager()
        mgr._recent_files = ["/a.json", "/b.json"]
        with patch("src.gui.recent_files_manager.QSettings"):
            mgr.clear()
        self.assertEqual(mgr._recent_files, [])


class TestOpenRecentFile(unittest.TestCase):
    """Tests for MainWindow._open_recent_file callback."""

    def setUp(self):
        self.stub = SimpleNamespace()
        self.stub._recent_mgr = _make_manager()
        self.stub._confirm_discard_changes = MagicMock(return_value=True)
        self.stub.load_data = MagicMock()
        self.stub._open_recent_file = MainWindow._open_recent_file.__get__(self.stub)
        self.stub._status_msg = None
        status_bar = MagicMock()
        status_bar.showMessage = lambda msg, timeout=0: setattr(self.stub, "_status_msg", msg)
        self.stub.statusBar = lambda: status_bar

    def test_nonexistent_file_removed_from_list(self):
        path = "/nonexistent/path.json"
        self.stub._recent_mgr._recent_files = [path]
        with patch("src.gui.recent_files_manager.QSettings"), \
             patch("os.path.exists", return_value=False):
            self.stub._open_recent_file(path)
        self.assertNotIn(path, self.stub._recent_mgr._recent_files)

    def test_nonexistent_file_shows_status_message(self):
        path = "/nonexistent/path.json"
        self.stub._recent_mgr._recent_files = [path]
        with patch("src.gui.recent_files_manager.QSettings"), \
             patch("os.path.exists", return_value=False):
            self.stub._open_recent_file(path)
        self.assertIsNotNone(self.stub._status_msg)
        self.assertIn("path.json", self.stub._status_msg)

    def test_existing_file_calls_load_data(self):
        path = "/exists/model.ply"
        self.stub._recent_mgr._recent_files = [path]
        with patch("os.path.exists", return_value=True):
            self.stub._open_recent_file(path)
        self.stub.load_data.assert_called_once_with(path)

    def test_discard_changes_cancelled_skips_load(self):
        path = "/exists/model.ply"
        self.stub._recent_mgr._recent_files = [path]
        self.stub._confirm_discard_changes.return_value = False
        with patch("os.path.exists", return_value=True):
            self.stub._open_recent_file(path)
        self.stub.load_data.assert_not_called()


class TestLoadSaveRecentFilesQSettings(unittest.TestCase):
    def test_load_recent_files_from_settings(self):
        expected = ["/a.json", "/b.json"]
        with patch("src.gui.recent_files_manager.QSettings") as MockQSettings:
            instance = MockQSettings.return_value
            instance.value.return_value = expected
            mgr = RecentFilesManager(parent=None)
        self.assertEqual(mgr._recent_files, expected)

    def test_save_recent_files_to_settings(self):
        mgr = _make_manager()
        mgr._recent_files = ["/x.json"]
        with patch("src.gui.recent_files_manager.QSettings") as MockQSettings:
            instance = MockQSettings.return_value
            mgr._save()
            instance.setValue.assert_called_once_with("recentFiles", ["/x.json"])

    def test_load_handles_missing_key(self):
        with patch("src.gui.recent_files_manager.QSettings") as MockQSettings:
            instance = MockQSettings.return_value
            instance.value.return_value = None
            mgr = RecentFilesManager(parent=None)
        self.assertEqual(mgr._recent_files, [])


if __name__ == "__main__":
    unittest.main()
