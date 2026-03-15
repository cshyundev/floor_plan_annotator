"""Tests for annotation_transformer module."""

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from src.map_align.annotation_transformer import (
    _compose_quaternion,
    _transform_point,
    invert_rigid_transform,
    transform_annotations,
)


# ─── _transform_point ───


def test_transform_point_identity():
    """Identity matrix should not change the point."""
    point = [1.0, 2.0, 3.0]
    result = _transform_point(point, np.eye(4))
    np.testing.assert_allclose(result, point)


def test_transform_point_translation():
    """Pure translation should shift the point."""
    tf = np.eye(4)
    tf[:3, 3] = [10.0, 20.0, 30.0]
    result = _transform_point([1.0, 2.0, 3.0], tf)
    np.testing.assert_allclose(result, [11.0, 22.0, 33.0])


def test_transform_point_90deg_z_rotation():
    """90 degree rotation around Z axis: (1,0,0) → (0,1,0)."""
    r = Rotation.from_euler("z", 90, degrees=True)
    tf = np.eye(4)
    tf[:3, :3] = r.as_matrix()
    result = _transform_point([1.0, 0.0, 0.0], tf)
    np.testing.assert_allclose(result, [0.0, 1.0, 0.0], atol=1e-10)


# ─── _compose_quaternion ───


def test_compose_quaternion_identity_tf():
    """Identity tf should preserve the original quaternion."""
    r = Rotation.from_euler("z", 90, degrees=True)
    q_xyzw = r.as_quat()
    quat_wxyz = [q_xyzw[3], q_xyzw[0], q_xyzw[1], q_xyzw[2]]
    result = _compose_quaternion(np.eye(4), quat_wxyz)
    np.testing.assert_allclose(result, quat_wxyz, atol=1e-10)


def test_compose_quaternion_identity_original():
    """Composing with identity quaternion should give tf rotation."""
    r = Rotation.from_euler("z", 45, degrees=True)
    tf = np.eye(4)
    tf[:3, :3] = r.as_matrix()

    # Identity quaternion [w,x,y,z] = [1,0,0,0]
    result = _compose_quaternion(tf, [1.0, 0.0, 0.0, 0.0])
    expected_xyzw = r.as_quat()
    expected_wxyz = [expected_xyzw[3], expected_xyzw[0], expected_xyzw[1], expected_xyzw[2]]
    np.testing.assert_allclose(result, expected_wxyz, atol=1e-10)


def test_compose_quaternion_two_rotations():
    """Composing two 90-deg Z rotations should give 180-deg Z rotation."""
    r90 = Rotation.from_euler("z", 90, degrees=True)
    tf = np.eye(4)
    tf[:3, :3] = r90.as_matrix()

    q90_xyzw = r90.as_quat()
    q90_wxyz = [q90_xyzw[3], q90_xyzw[0], q90_xyzw[1], q90_xyzw[2]]

    result = _compose_quaternion(tf, q90_wxyz)

    r180 = Rotation.from_euler("z", 180, degrees=True)
    q180_xyzw = r180.as_quat()
    q180_wxyz = [q180_xyzw[3], q180_xyzw[0], q180_xyzw[1], q180_xyzw[2]]

    # Quaternions can be negated and represent the same rotation
    if np.dot(result, q180_wxyz) < 0:
        result = [-r for r in result]
    np.testing.assert_allclose(result, q180_wxyz, atol=1e-10)


# ─── invert_rigid_transform ───


def test_invert_identity():
    """Inverse of identity is identity."""
    result = invert_rigid_transform(np.eye(4))
    np.testing.assert_allclose(result, np.eye(4))


def test_invert_roundtrip():
    """T @ T_inv should give identity."""
    r = Rotation.from_euler("xyz", [30, 45, 60], degrees=True)
    T = np.eye(4)
    T[:3, :3] = r.as_matrix()
    T[:3, 3] = [1.5, -2.3, 0.7]

    T_inv = invert_rigid_transform(T)
    np.testing.assert_allclose(T @ T_inv, np.eye(4), atol=1e-10)
    np.testing.assert_allclose(T_inv @ T, np.eye(4), atol=1e-10)


# ─── transform_annotations ───


def _sample_annotations() -> dict:
    """Create a small test annotations dict."""
    return {
        "version": "1.0",
        "layout": {
            "walls": [
                [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
            ],
            "rooms": [
                {
                    "id": "1",
                    "type": "Bedroom",
                    "points": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0]],
                },
            ],
        },
        "zones": [
            {
                "id": "z1",
                "type": "Danger Zone",
                "points": [[2.0, 2.0, 0.0], [3.0, 2.0, 0.0]],
            },
        ],
        "objects": [
            {
                "id": "o1",
                "type": "Bed",
                "center": [5.0, 5.0, 0.5],
                "extent": [2.0, 1.5, 1.0],
                "rotation": [1.0, 0.0, 0.0, 0.0],  # identity quaternion
            },
        ],
    }


def test_transform_annotations_identity():
    """Identity transform should not change any coordinates."""
    data = _sample_annotations()
    result = transform_annotations(data, np.eye(4))

    np.testing.assert_allclose(
        result["layout"]["walls"][0][0], [1.0, 0.0, 0.0],
    )
    np.testing.assert_allclose(
        result["objects"][0]["center"], [5.0, 5.0, 0.5],
    )
    np.testing.assert_allclose(
        result["objects"][0]["extent"], [2.0, 1.5, 1.0],
    )


def test_transform_annotations_translation():
    """Translation should shift all point coordinates but not extent."""
    tf = np.eye(4)
    tf[:3, 3] = [10.0, 20.0, 0.0]

    data = _sample_annotations()
    result = transform_annotations(data, tf)

    # Wall point shifted
    np.testing.assert_allclose(result["layout"]["walls"][0][0], [11.0, 20.0, 0.0])
    # Room point shifted
    np.testing.assert_allclose(result["layout"]["rooms"][0]["points"][1], [11.0, 20.0, 0.0])
    # Zone point shifted
    np.testing.assert_allclose(result["zones"][0]["points"][0], [12.0, 22.0, 0.0])
    # Object center shifted
    np.testing.assert_allclose(result["objects"][0]["center"], [15.0, 25.0, 0.5])
    # Object extent unchanged
    np.testing.assert_allclose(result["objects"][0]["extent"], [2.0, 1.5, 1.0])


def test_transform_annotations_does_not_mutate_input():
    """transform_annotations should return a deep copy."""
    data = _sample_annotations()
    original_wall = data["layout"]["walls"][0][0].copy()
    tf = np.eye(4)
    tf[:3, 3] = [100.0, 100.0, 100.0]

    transform_annotations(data, tf)
    assert data["layout"]["walls"][0][0] == original_wall


def test_roundtrip_transform_restore():
    """Transform with T then T_inv should restore original coordinates."""
    r = Rotation.from_euler("z", 45, degrees=True)
    T = np.eye(4)
    T[:3, :3] = r.as_matrix()
    T[:3, 3] = [3.0, -1.0, 0.0]
    T_inv = invert_rigid_transform(T)

    data = _sample_annotations()
    transformed = transform_annotations(data, T)
    restored = transform_annotations(transformed, T_inv)

    # Check walls
    for i, wall in enumerate(data["layout"]["walls"]):
        for j, pt in enumerate(wall):
            np.testing.assert_allclose(
                restored["layout"]["walls"][i][j], pt, atol=1e-10,
            )

    # Check rooms
    for i, room in enumerate(data["layout"]["rooms"]):
        for j, pt in enumerate(room["points"]):
            np.testing.assert_allclose(
                restored["layout"]["rooms"][i]["points"][j], pt, atol=1e-10,
            )

    # Check objects
    orig_obj = data["objects"][0]
    rest_obj = restored["objects"][0]
    np.testing.assert_allclose(rest_obj["center"], orig_obj["center"], atol=1e-10)
    np.testing.assert_allclose(rest_obj["extent"], orig_obj["extent"], atol=1e-10)

    # Quaternion round-trip (may be negated)
    q_orig = np.array(orig_obj["rotation"])
    q_rest = np.array(rest_obj["rotation"])
    if np.dot(q_orig, q_rest) < 0:
        q_rest = -q_rest
    np.testing.assert_allclose(q_rest, q_orig, atol=1e-10)


def test_transform_annotations_empty_fields():
    """Should handle missing optional fields gracefully."""
    data = {"version": "1.0", "layout": {}}
    result = transform_annotations(data, np.eye(4))
    assert result["version"] == "1.0"
    assert result["layout"] == {}
