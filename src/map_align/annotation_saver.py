"""Save aligned annotations to the source directory."""

import json
import os
from datetime import datetime, timezone

import numpy as np

from src.core.coordinate_system import CoordinateSystem
from src.map_align.annotation_transformer import (
    flip_floor_v_annotations,
    invert_rigid_transform,
    transform_annotations,
)


def _resolve_coordinate_system(data: dict) -> CoordinateSystem:
    """Read coordinate system from annotations dict."""
    cs_field = data.get("coordinate_system", "ros")
    if isinstance(cs_field, str):
        return CoordinateSystem.from_preset(cs_field)
    return CoordinateSystem.from_dict(cs_field)


def save_aligned_annotations(
    source_path: str,
    reference_path: str,
    tf_src_to_ref: np.ndarray,
    icp_fitness: float,
    icp_rmse: float,
    source_bounds: tuple[list, list] | None = None,
    reference_bounds: tuple[list, list] | None = None,
) -> str:
    """Transform reference annotations and save to source directory.

    Handles the coordinate convention used by the floor plan annotator:
    the annotator stores scene coordinates (with floor_v axis flipped for
    ROS/OpenCV) in annotations.json. This function converts scene→world
    before applying the rigid transform, then converts world→scene for the
    output, ensuring the result is compatible with the annotator.

    Args:
        source_path: Path to the source map file.
        reference_path: Path to the reference map file.
        tf_src_to_ref: 4x4 ICP result matrix (source → reference).
        icp_fitness: ICP overlap fitness score.
        icp_rmse: ICP inlier RMSE.
        source_bounds: Optional (bounds_min, bounds_max) each as [x, y, z].
        reference_bounds: Optional (bounds_min, bounds_max) for reference cloud.

    Returns:
        Path to the saved annotations.json file.
    """
    tf_ref_to_src = invert_rigid_transform(tf_src_to_ref)

    # Look for annotations.json next to the reference file
    ref_dir = os.path.dirname(os.path.abspath(reference_path))
    ref_annotations_path = os.path.join(ref_dir, "annotations.json")

    if os.path.isfile(ref_annotations_path):
        with open(ref_annotations_path, "r") as f:
            ref_data = json.load(f)

        cs = _resolve_coordinate_system(ref_data)

        # Scene → world → transform → world → scene pipeline
        if cs.flip_floor_v:
            ref_bounds = _resolve_bounds(ref_data, reference_bounds)
            if ref_bounds is not None:
                flip_floor_v_annotations(
                    ref_data, ref_bounds[0], ref_bounds[1],
                    floor_v_axis=cs.floor_axes[1], up_axis=cs.up_axis,
                )

        result = transform_annotations(ref_data, tf_ref_to_src)

        if cs.flip_floor_v and source_bounds is not None:
            flip_floor_v_annotations(
                result, source_bounds[0], source_bounds[1],
                floor_v_axis=cs.floor_axes[1], up_axis=cs.up_axis,
            )
    else:
        result = _create_skeleton()

    # Add alignment metadata
    result["alignment"] = _build_alignment_meta(
        tf_ref_to_src=tf_ref_to_src,
        reference_path=reference_path,
        icp_fitness=icp_fitness,
        icp_rmse=icp_rmse,
    )

    # Update source metadata
    source_meta = result.get("source", {})
    source_meta["file_name"] = os.path.basename(source_path)
    if source_bounds is not None:
        source_meta["bounds_min"] = source_bounds[0]
        source_meta["bounds_max"] = source_bounds[1]
    result["source"] = source_meta

    # Update timestamps
    now = datetime.now(timezone.utc).isoformat()
    result["modified_at"] = now
    if "created_at" not in result:
        result["created_at"] = now

    # Save to source directory
    source_dir = os.path.dirname(os.path.abspath(source_path))
    output_path = os.path.join(source_dir, "annotations.json")
    os.makedirs(source_dir, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return output_path


def _resolve_bounds(
    data: dict,
    explicit_bounds: tuple[list, list] | None,
) -> tuple[list, list] | None:
    """Get bounds from explicit parameter or from annotations source metadata."""
    if explicit_bounds is not None:
        return explicit_bounds
    source = data.get("source", {})
    bmin = source.get("bounds_min")
    bmax = source.get("bounds_max")
    if bmin is not None and bmax is not None:
        return (bmin, bmax)
    return None


def _create_skeleton() -> dict:
    """Create an empty annotations dictionary with the v1.0 schema."""
    return {
        "version": "1.0",
        "layout": {
            "walls": [],
            "rooms": [],
        },
        "objects": [],
        "zones": [],
    }


def _build_alignment_meta(
    tf_ref_to_src: np.ndarray,
    reference_path: str,
    icp_fitness: float,
    icp_rmse: float,
) -> dict:
    """Build alignment metadata dictionary.

    Args:
        tf_ref_to_src: 4x4 reference-to-source transformation matrix.
        reference_path: Path to the reference map file.
        icp_fitness: ICP overlap fitness score.
        icp_rmse: ICP inlier RMSE.

    Returns:
        Alignment metadata dictionary.
    """
    return {
        "transform_4x4": tf_ref_to_src.tolist(),
        "direction": "reference_to_source",
        "description": "p_src = T @ p_ref",
        "reference_file": os.path.basename(reference_path),
        "icp_fitness": round(icp_fitness, 6),
        "icp_rmse": round(icp_rmse, 6),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
