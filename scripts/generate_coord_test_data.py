"""Generate dummy 3D point cloud data for each coordinate system convention.

Creates an L-shaped room so the user can visually verify that the
coordinate system interpretation is correct (asymmetric shape makes
orientation errors obvious).

Coordinate conventions:
  - ROS:    X=forward, Y=left, Z=up       (Z-up)
  - OpenCV: X=right,   Y=down, Z=forward  (Y-down)
  - OpenGL: X=right,   Y=up,   Z=backward (Y-up)
"""

import open3d as o3d
import numpy as np
import os


def create_wall_points(start_2d, end_2d, height_range, up_axis, floor_axes,
                       num_points=5000):
    """Create wall points between two 2D floor positions.

    Args:
        start_2d: (h, v) start on the floor plane
        end_2d: (h, v) end on the floor plane
        height_range: (min_h, max_h) along the up axis
        up_axis: index of the vertical axis (0, 1, or 2)
        floor_axes: (h_axis, v_axis) indices
        num_points: number of random samples
    """
    t = np.random.rand(num_points)
    h = np.random.rand(num_points) * (height_range[1] - height_range[0]) + height_range[0]

    fh = np.interp(t, [0, 1], [start_2d[0], end_2d[0]])
    fv = np.interp(t, [0, 1], [start_2d[1], end_2d[1]])

    pts = np.zeros((num_points, 3))
    pts[:, floor_axes[0]] = fh
    pts[:, floor_axes[1]] = fv
    pts[:, up_axis] = h
    return pts


def create_floor_points(corners_2d, height, up_axis, floor_axes, num_points=20000):
    """Create floor points inside an L-shaped polygon.

    Uses rejection sampling within the bounding box.

    Args:
        corners_2d: list of (h, v) polygon vertices
        height: scalar height value on the up axis
        up_axis: index of the vertical axis
        floor_axes: (h_axis, v_axis)
        num_points: approximate target count
    """
    from matplotlib.path import Path
    poly = Path(corners_2d)

    hs = [c[0] for c in corners_2d]
    vs = [c[1] for c in corners_2d]
    h_min, h_max = min(hs), max(hs)
    v_min, v_max = min(vs), max(vs)

    # Over-sample then filter
    n_try = num_points * 3
    rand_h = np.random.rand(n_try) * (h_max - h_min) + h_min
    rand_v = np.random.rand(n_try) * (v_max - v_min) + v_min
    candidates = np.column_stack((rand_h, rand_v))
    mask = poly.contains_points(candidates)
    inside = candidates[mask][:num_points]

    pts = np.zeros((len(inside), 3))
    pts[:, floor_axes[0]] = inside[:, 0]
    pts[:, floor_axes[1]] = inside[:, 1]
    pts[:, up_axis] = height
    return pts


def generate_l_room(up_axis, floor_axes, up_direction, label):
    """Generate an L-shaped room point cloud.

    The L-shape on the floor plane:
        (0,0)---(8,0)
          |        |
          |   (8,4)---(5,4)
          |              |
        (0,6)-------(5,6)

    Args:
        up_axis: which axis is vertical (0, 1, or 2)
        floor_axes: (h_axis, v_axis) forming the floor plane
        up_direction: +1 (up is positive) or -1 (up is negative)
        label: string label for output file
    """
    wall_height = 3.0
    if up_direction == 1:
        floor_h = 0.0
        h_min, h_max = 0.0, wall_height
    else:
        floor_h = 0.0
        h_min, h_max = -wall_height, 0.0

    # L-shape vertices on the floor (h, v) coordinates
    corners = [(0, 0), (8, 0), (8, 4), (5, 4), (5, 6), (0, 6)]

    # Walls: consecutive edges
    walls = []
    for i in range(len(corners)):
        s = corners[i]
        e = corners[(i + 1) % len(corners)]
        walls.append(create_wall_points(s, e, (h_min, h_max), up_axis, floor_axes))

    # Floor
    floor_pts = create_floor_points(corners, floor_h, up_axis, floor_axes)

    # Ceiling
    ceiling_h = h_max if up_direction == 1 else h_min
    ceiling_pts = create_floor_points(corners, ceiling_h, up_axis, floor_axes,
                                      num_points=10000)

    all_pts = np.vstack(walls + [floor_pts, ceiling_pts])

    # Add noise
    all_pts += np.random.normal(0, 0.015, all_pts.shape)

    # Color by height
    heights = all_pts[:, up_axis]
    h_norm = (heights - heights.min()) / (heights.max() - heights.min() + 1e-9)
    colors = np.zeros_like(all_pts)
    colors[:, 0] = 1.0 - h_norm  # red at bottom
    colors[:, 2] = h_norm         # blue at top
    colors[:, 1] = 0.3            # slight green tint

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_pts)
    pcd.colors = o3d.utility.Vector3dVector(np.clip(colors, 0, 1))

    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"test_{label}.ply")
    o3d.io.write_point_cloud(path, pcd)
    print(f"[{label}] {len(all_pts)} points -> {path}")
    print(f"  up_axis={up_axis}, floor_axes={floor_axes}, up_dir={up_direction}")
    print(f"  height range: {heights.min():.2f} ~ {heights.max():.2f}")
    return path


def main():
    np.random.seed(42)

    # ROS: Z-up, floor = XY
    generate_l_room(up_axis=2, floor_axes=(0, 1), up_direction=1, label="ros_z_up")

    # OpenCV: Y-down (up_direction=-1, up_axis=1), floor = XZ
    generate_l_room(up_axis=1, floor_axes=(0, 2), up_direction=-1, label="opencv_y_down")

    # OpenGL: Y-up, floor = XZ
    generate_l_room(up_axis=1, floor_axes=(0, 2), up_direction=1, label="opengl_y_up")

    print("\nDone! Load each file and select the matching preset:")
    print("  test_ros_z_up.ply     -> Preset: ROS (Z-up)")
    print("  test_opencv_y_down.ply -> Preset: OpenCV (Y-down)")
    print("  test_opengl_y_up.ply  -> Preset: OpenGL (Y-up)")
    print("\nThe L-shape should look the same orientation in 2D for all three.")


if __name__ == "__main__":
    main()
