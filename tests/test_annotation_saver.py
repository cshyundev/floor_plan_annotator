"""Tests for annotation_saver module."""

import json
import os

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from src.map_align.annotation_saver import save_aligned_annotations
from src.map_align.annotation_transformer import invert_rigid_transform


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temp workspace with reference and source directories."""
    ref_dir = tmp_path / "reference"
    src_dir = tmp_path / "source"
    ref_dir.mkdir()
    src_dir.mkdir()

    ref_file = ref_dir / "mesh_ref.ply"
    src_file = src_dir / "mesh_src.ply"
    ref_file.touch()
    src_file.touch()

    return {
        "ref_path": str(ref_file),
        "src_path": str(src_file),
        "ref_dir": str(ref_dir),
        "src_dir": str(src_dir),
    }


def _make_ref_annotations(ref_dir: str, *, with_bounds: bool = False) -> dict:
    """Create a reference annotations.json and return the data.

    When with_bounds=True, adds coordinate_system and source.bounds fields
    to enable the scene convention flip pipeline.
    """
    data = {
        "version": "1.0",
        "coordinate_system": "ros",
        "layout": {
            "walls": [[[1.0, 2.0, 0.0], [3.0, 4.0, 0.0]]],
            "rooms": [
                {
                    "id": "r1",
                    "type": "Bedroom",
                    "points": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]],
                },
            ],
        },
        "objects": [
            {
                "id": "o1",
                "type": "Table",
                "center": [5.0, 5.0, 0.5],
                "extent": [1.0, 0.8, 0.75],
                "rotation": [1.0, 0.0, 0.0, 0.0],
            },
        ],
        "zones": [],
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    if with_bounds:
        data["source"] = {
            "file_name": "mesh_ref.ply",
            "bounds_min": [0.0, 0.0, 0.0],
            "bounds_max": [10.0, 10.0, 3.0],
        }
    path = os.path.join(ref_dir, "annotations.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return data


class TestWithReferenceAnnotations:
    """Tests when reference has annotations.json."""

    def test_saves_to_source_dir(self, tmp_workspace):
        """Output should be saved in source directory."""
        _make_ref_annotations(tmp_workspace["ref_dir"])
        tf = np.eye(4)

        result_path = save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=tf,
            icp_fitness=0.95,
            icp_rmse=0.03,
        )

        assert result_path == os.path.join(tmp_workspace["src_dir"], "annotations.json")
        assert os.path.isfile(result_path)

    def test_alignment_metadata_complete(self, tmp_workspace):
        """Alignment metadata should have all required fields."""
        _make_ref_annotations(tmp_workspace["ref_dir"])
        tf = np.eye(4)

        save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=tf,
            icp_fitness=0.95,
            icp_rmse=0.03,
        )

        output_path = os.path.join(tmp_workspace["src_dir"], "annotations.json")
        with open(output_path) as f:
            saved = json.load(f)

        alignment = saved["alignment"]
        assert "transform_4x4" in alignment
        assert alignment["direction"] == "reference_to_source"
        assert alignment["description"] == "p_src = T @ p_ref"
        assert alignment["reference_file"] == "mesh_ref.ply"
        assert alignment["icp_fitness"] == 0.95
        assert alignment["icp_rmse"] == 0.03
        assert "created_at" in alignment

    def test_saved_matrix_is_inverse_of_icp(self, tmp_workspace):
        """The stored transform should be the inverse of the ICP result."""
        _make_ref_annotations(tmp_workspace["ref_dir"])
        r = Rotation.from_euler("z", 30, degrees=True)
        tf_src_to_ref = np.eye(4)
        tf_src_to_ref[:3, :3] = r.as_matrix()
        tf_src_to_ref[:3, 3] = [1.0, 2.0, 0.0]

        save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=tf_src_to_ref,
            icp_fitness=0.9,
            icp_rmse=0.05,
        )

        output_path = os.path.join(tmp_workspace["src_dir"], "annotations.json")
        with open(output_path) as f:
            saved = json.load(f)

        saved_tf = np.array(saved["alignment"]["transform_4x4"])
        expected_inv = invert_rigid_transform(tf_src_to_ref)
        np.testing.assert_allclose(saved_tf, expected_inv, atol=1e-10)

    def test_source_bounds_stored(self, tmp_workspace):
        """Source bounds should be stored when provided."""
        _make_ref_annotations(tmp_workspace["ref_dir"])

        save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=np.eye(4),
            icp_fitness=0.9,
            icp_rmse=0.05,
            source_bounds=([0.0, 0.0, 0.0], [10.0, 10.0, 3.0]),
        )

        output_path = os.path.join(tmp_workspace["src_dir"], "annotations.json")
        with open(output_path) as f:
            saved = json.load(f)

        assert saved["source"]["bounds_min"] == [0.0, 0.0, 0.0]
        assert saved["source"]["bounds_max"] == [10.0, 10.0, 3.0]


class TestSceneConvention:
    """Tests for scene coordinate convention (Y-flip for ROS)."""

    def test_identity_transform_preserves_scene_coords(self, tmp_workspace):
        """Identity transform with same bounds should preserve coordinates."""
        _make_ref_annotations(tmp_workspace["ref_dir"], with_bounds=True)
        bounds = ([0.0, 0.0, 0.0], [10.0, 10.0, 3.0])

        save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=np.eye(4),
            icp_fitness=1.0,
            icp_rmse=0.0,
            source_bounds=bounds,
            reference_bounds=bounds,
        )

        output_path = os.path.join(tmp_workspace["src_dir"], "annotations.json")
        with open(output_path) as f:
            saved = json.load(f)

        # With identity transform and same bounds, scene coords should be preserved
        np.testing.assert_allclose(
            saved["layout"]["walls"][0][0], [1.0, 2.0, 0.0], atol=1e-10,
        )
        np.testing.assert_allclose(
            saved["objects"][0]["center"][:2], [5.0, 5.0], atol=1e-10,
        )

    def test_translation_with_scene_flip(self, tmp_workspace):
        """Translation should produce correct scene coordinates."""
        _make_ref_annotations(tmp_workspace["ref_dir"], with_bounds=True)
        ref_bounds = ([0.0, 0.0, 0.0], [10.0, 10.0, 3.0])
        # Source cloud shifted by tx=5 → source X range [5, 15]
        src_bounds = ([5.0, 0.0, 0.0], [15.0, 10.0, 3.0])

        tf_src_to_ref = np.eye(4)
        tf_src_to_ref[:3, 3] = [-5.0, 0.0, 0.0]
        # T_inv: translates reference by [+5, 0, 0] → source frame

        save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=tf_src_to_ref,
            icp_fitness=1.0,
            icp_rmse=0.0,
            source_bounds=src_bounds,
            reference_bounds=ref_bounds,
        )

        output_path = os.path.join(tmp_workspace["src_dir"], "annotations.json")
        with open(output_path) as f:
            saved = json.load(f)

        # Wall start: scene [1, 2, 0]
        # → un-flip Y: world [1, (0+10)-2, 0] = [1, 8, 0]
        # → translate +5 in X: [6, 8, 0]
        # → flip Y with src bounds: [6, (0+10)-8, 0] = [6, 2, 0]
        np.testing.assert_allclose(
            saved["layout"]["walls"][0][0], [6.0, 2.0, 0.0], atol=1e-10,
        )

    def test_object_rotation_flipped(self, tmp_workspace):
        """Object rotation quaternion should follow scene convention."""
        ref_dir = tmp_workspace["ref_dir"]
        ref_bounds = ([0.0, 0.0, 0.0], [10.0, 10.0, 3.0])
        src_bounds = ref_bounds  # Same bounds for simplicity

        # Create annotations with a 90-degree scene rotation
        import math
        scene_angle = math.radians(-90)  # scene angle (ROS: negated world angle)
        quat = [math.cos(scene_angle / 2), 0.0, 0.0, math.sin(scene_angle / 2)]

        data = {
            "version": "1.0",
            "coordinate_system": "ros",
            "objects": [
                {
                    "id": "o1", "type": "Table",
                    "center": [5.0, 5.0, 0.5],
                    "extent": [1.0, 0.8, 0.75],
                    "rotation": quat,
                },
            ],
            "layout": {"walls": [], "rooms": []},
            "zones": [],
            "source": {
                "file_name": "mesh_ref.ply",
                "bounds_min": ref_bounds[0],
                "bounds_max": ref_bounds[1],
            },
        }
        path = os.path.join(ref_dir, "annotations.json")
        with open(path, "w") as f:
            json.dump(data, f)

        # Identity transform — rotation should be preserved
        save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=np.eye(4),
            icp_fitness=1.0,
            icp_rmse=0.0,
            source_bounds=src_bounds,
            reference_bounds=ref_bounds,
        )

        output_path = os.path.join(tmp_workspace["src_dir"], "annotations.json")
        with open(output_path) as f:
            saved = json.load(f)

        # With identity transform and same bounds, quaternion should be preserved
        np.testing.assert_allclose(saved["objects"][0]["rotation"], quat, atol=1e-10)


class TestWithoutReferenceAnnotations:
    """Tests when reference has no annotations.json."""

    def test_creates_skeleton(self, tmp_workspace):
        """Should create a skeleton annotations.json with empty arrays."""
        save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=np.eye(4),
            icp_fitness=0.0,
            icp_rmse=0.0,
        )

        output_path = os.path.join(tmp_workspace["src_dir"], "annotations.json")
        with open(output_path) as f:
            saved = json.load(f)

        assert saved["version"] == "1.0"
        assert saved["layout"]["walls"] == []
        assert saved["layout"]["rooms"] == []
        assert saved["objects"] == []
        assert saved["zones"] == []

    def test_skeleton_has_alignment_meta(self, tmp_workspace):
        """Skeleton should still include alignment metadata."""
        save_aligned_annotations(
            source_path=tmp_workspace["src_path"],
            reference_path=tmp_workspace["ref_path"],
            tf_src_to_ref=np.eye(4),
            icp_fitness=0.5,
            icp_rmse=0.1,
        )

        output_path = os.path.join(tmp_workspace["src_dir"], "annotations.json")
        with open(output_path) as f:
            saved = json.load(f)

        assert "alignment" in saved
        assert saved["alignment"]["icp_fitness"] == 0.5
        assert saved["alignment"]["reference_file"] == "mesh_ref.ply"
