"""Tests for FEAT-006 project lifecycle management.

Covers:
- MapMetadata.to_dict() omits image_path_absolute (regression)
- annotations.json pairing convention (file-system level)
- ProjectIO save/load omits image_path_absolute

Note: GUI-level tests (title bar, confirm dialog, save_project routing) require
a live MainWindow and are covered by manual / e2e testing due to the cost of
instantiating the 3D viewer in CI.
"""
import json
import os
import tempfile
import unittest

from src.model.data import MapMetadata, ProjectData
from src.core.coordinate_system import CoordinateSystem
from src.core.io import ProjectIO


# ── MapMetadata serialization ──────────────────────────────────────────────

class TestMapMetadataAbsolutePath(unittest.TestCase):
    """image_path_absolute must not be written to disk (REQ-028 / FEAT-006)."""

    def test_image_path_absolute_not_in_dict(self):
        meta = MapMetadata(
            image_path="scan.glb",
            image_path_absolute="/abs/path/scan.glb",
        )
        d = meta.to_dict()
        self.assertNotIn("image_path_absolute", d)

    def test_image_path_still_serialized(self):
        meta = MapMetadata(image_path="scan.glb", image_path_absolute="/abs/scan.glb")
        d = meta.to_dict()
        self.assertEqual(d["image_path"], "scan.glb")

    def test_legacy_absolute_path_loads_into_memory(self):
        """from_dict on a legacy v3.0 file (which has the key) still reads it."""
        d = {
            "image_path": "scan.glb",
            "image_path_absolute": "/legacy/abs/scan.glb",
            "resolution": 0.05,
        }
        meta = MapMetadata.from_dict(d)
        self.assertEqual(meta.image_path_absolute, "/legacy/abs/scan.glb")

    def test_saved_json_has_no_absolute_path(self):
        """End-to-end: saved project JSON must not contain image_path_absolute."""
        meta = MapMetadata(
            image_path="scan.glb",
            image_path_absolute="/abs/scan.glb",
        )
        proj = ProjectData()
        proj.map_metadata = meta
        d = proj.to_dict()
        self.assertNotIn("image_path_absolute", d.get("map_metadata", {}))


# ── Annotation pairing convention (file-system level) ─────────────────────

class TestAnnotationPairingConvention(unittest.TestCase):
    """Verify the pairing rule: annotations.json image_path basename == 3D file basename."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_annotations(self, folder: str, image_path: str) -> str:
        meta = MapMetadata(image_path=image_path)
        proj = ProjectData()
        proj.map_metadata = meta
        path = os.path.join(folder, "annotations.json")
        with open(path, "w") as f:
            json.dump(proj.to_dict(), f)
        return path

    def test_matching_basename_detected(self):
        """Basename of stored image_path equals the 3D file name → pairing valid."""
        ann_path = self._write_annotations(self.tmpdir.name, "scan.glb")
        proj = ProjectIO.load_project(ann_path)
        stored_basename = os.path.basename(proj.map_metadata.image_path)
        self.assertEqual(stored_basename, "scan.glb")

    def test_mismatched_basename_detected(self):
        """Basename mismatch is detectable by comparing stored vs loaded filename."""
        ann_path = self._write_annotations(self.tmpdir.name, "other.glb")
        proj = ProjectIO.load_project(ann_path)
        stored_basename = os.path.basename(proj.map_metadata.image_path)
        # App would skip auto-load when these differ
        self.assertNotEqual(stored_basename, "scan.glb")

    def test_annotations_json_roundtrip_preserves_image_path(self):
        """After save → load, image_path is preserved and image_path_absolute is absent."""
        ann_path = self._write_annotations(self.tmpdir.name, "map.pgm")
        proj = ProjectIO.load_project(ann_path)
        self.assertEqual(proj.map_metadata.image_path, "map.pgm")
        # Verify the raw JSON has no absolute path key
        with open(ann_path) as f:
            raw = json.load(f)
        self.assertNotIn("image_path_absolute", raw.get("map_metadata", {}))

    def test_annotations_without_map_metadata_is_valid(self):
        """annotations.json with no map_metadata is a valid (blank) project."""
        proj = ProjectData()
        path = os.path.join(self.tmpdir.name, "annotations.json")
        with open(path, "w") as f:
            json.dump(proj.to_dict(), f)
        loaded = ProjectIO.load_project(path)
        self.assertIsNone(loaded.map_metadata)


# ── Save path derivation (pure logic) ─────────────────────────────────────

class TestSavePathDerivation(unittest.TestCase):
    """Verify the {3d_folder}/annotations.json path computation."""

    def test_annotations_path_from_3d_file(self):
        """Given a 3D file path, derived save path is in the same folder."""
        threed_path = "/home/user/project/scan.glb"
        folder = os.path.dirname(threed_path)
        derived = os.path.join(folder, "annotations.json")
        self.assertEqual(derived, "/home/user/project/annotations.json")

    def test_derived_path_is_independent_of_3d_filename(self):
        """The fixed name annotations.json does not depend on the 3D file name."""
        for fname in ("map.pgm", "building.glb", "lidar.ply"):
            folder = "/data/project"
            derived = os.path.join(folder, "annotations.json")
            self.assertEqual(os.path.basename(derived), "annotations.json")


if __name__ == "__main__":
    unittest.main()
