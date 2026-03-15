"""Transform annotation coordinates using a 4x4 rigid transformation matrix."""

import copy

import numpy as np
from scipy.spatial.transform import Rotation


def _transform_point(point: list, tf: np.ndarray) -> list:
    """Transform a 3D point using a 4x4 homogeneous matrix.

    Args:
        point: [x, y, z] coordinates.
        tf: 4x4 homogeneous transformation matrix.

    Returns:
        Transformed [x, y, z] as a list of floats.
    """
    p = np.array([point[0], point[1], point[2], 1.0])
    result = tf @ p
    return [float(result[0]), float(result[1]), float(result[2])]


def _compose_quaternion(tf: np.ndarray, quat_wxyz: list) -> list:
    """Compose the rotation from tf with an existing quaternion.

    Computes q_result = q_tf * q_original (Hamilton product).

    Args:
        tf: 4x4 homogeneous transformation matrix.
        quat_wxyz: Original quaternion in [w, x, y, z] order.

    Returns:
        Composed quaternion in [w, x, y, z] order.
    """
    # Extract rotation from tf matrix
    r_tf = Rotation.from_matrix(tf[:3, :3])

    # scipy uses [x, y, z, w] internally
    q_orig_xyzw = [quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]]
    r_orig = Rotation.from_quat(q_orig_xyzw)

    # Compose: apply tf rotation then original rotation
    r_composed = r_tf * r_orig
    q_xyzw = r_composed.as_quat()

    # Convert back to [w, x, y, z]
    return [float(q_xyzw[3]), float(q_xyzw[0]), float(q_xyzw[1]), float(q_xyzw[2])]


def invert_rigid_transform(T: np.ndarray) -> np.ndarray:
    """Compute the inverse of a rigid transformation matrix.

    Uses R^T / -R^T @ t for numerical stability instead of np.linalg.inv.

    Args:
        T: 4x4 homogeneous rigid transformation matrix.

    Returns:
        4x4 inverse transformation matrix.
    """
    R = T[:3, :3]
    t = T[:3, 3]
    T_inv = np.eye(4)
    T_inv[:3, :3] = R.T
    T_inv[:3, 3] = -R.T @ t
    return T_inv


def transform_annotations(data: dict, tf_ref_to_src: np.ndarray) -> dict:
    """Transform all annotation coordinates from reference frame to source frame.

    Args:
        data: Annotations dictionary (v1.0 schema).
        tf_ref_to_src: 4x4 matrix mapping reference coordinates to source coordinates.

    Returns:
        Deep copy of data with all coordinates transformed.
    """
    result = copy.deepcopy(data)
    tf = tf_ref_to_src

    # Transform walls: each wall is [[x,y,z], [x,y,z]]
    layout = result.get("layout", {})
    if "walls" in layout:
        layout["walls"] = [
            [_transform_point(p, tf) for p in wall]
            for wall in layout["walls"]
        ]

    # Transform rooms: each room has "points" list of [x,y,z]
    if "rooms" in layout:
        for room in layout["rooms"]:
            room["points"] = [_transform_point(p, tf) for p in room["points"]]

    # Transform zones: same structure as rooms
    if "zones" in result:
        for zone in result["zones"]:
            zone["points"] = [_transform_point(p, tf) for p in zone["points"]]

    # Transform objects: center + rotation quaternion composition
    if "objects" in result:
        for obj in result["objects"]:
            obj["center"] = _transform_point(obj["center"], tf)
            if "rotation" in obj:
                obj["rotation"] = _compose_quaternion(tf, obj["rotation"])
            # extent is unchanged (rigid transform preserves dimensions)

    return result


def flip_floor_v_annotations(
    data: dict,
    bounds_min: list,
    bounds_max: list,
    floor_v_axis: int = 1,
    up_axis: int = 2,
) -> dict:
    """Flip the floor-vertical axis of all annotation coordinates.

    The annotator's canvas uses screen-Y (top-down), while 3D world data uses
    Y-up for ROS. This function converts between the two conventions by
    reflecting the floor_v coordinate: new_v = (min_v + max_v) - old_v.

    The operation is its own inverse: applying it twice restores originals.

    Also negates object rotation quaternion around the up axis, since a
    Y-mirror flips rotation direction in the floor plane.

    Args:
        data: Annotations dictionary (v1.0 schema). Modified in-place.
        bounds_min: [x, y, z] minimum bounds of the relevant point cloud.
        bounds_max: [x, y, z] maximum bounds of the relevant point cloud.
        floor_v_axis: Index of the floor-vertical axis in 3D points (1 for ROS).
        up_axis: Index of the up axis (2 for ROS).

    Returns:
        The same dict, modified in-place.
    """
    fv = floor_v_axis
    v_sum = bounds_min[fv] + bounds_max[fv]

    def flip_point(pt: list) -> list:
        pt[fv] = v_sum - pt[fv]
        return pt

    # Flip all geometry points
    layout = data.get("layout", {})
    for wall in layout.get("walls", []):
        for pt in wall:
            flip_point(pt)

    for room in layout.get("rooms", []):
        for pt in room["points"]:
            flip_point(pt)

    for zone in data.get("zones", []):
        for pt in zone["points"]:
            flip_point(pt)

    # Flip object centers and negate rotation
    for obj in data.get("objects", []):
        flip_point(obj["center"])
        if "rotation" in obj:
            # Negate the up-axis quaternion component to reverse rotation direction
            obj["rotation"][1 + up_axis] *= -1

    return data
