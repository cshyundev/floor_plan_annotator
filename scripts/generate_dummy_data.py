import open3d as o3d
import numpy as np
import os

def create_wall(start, end, height, num_points=10000):
    """Creates a wall of points between start and end coordinates with given height."""
    vec = end - start
    length = np.linalg.norm(vec)
    direction = vec / length
    
    # Generate points along the wall
    t = np.random.rand(num_points) * length
    h = np.random.rand(num_points) * height
    
    points = start + np.outer(t, direction)
    points[:, 2] = h
    return points

def create_floor(width, depth, num_points=50000):
    """Creates a floor plane of points."""
    x = np.random.rand(num_points) * width
    y = np.random.rand(num_points) * depth
    z = np.zeros(num_points)
    return np.column_stack((x, y, z))

def main():
    width = 10.0
    depth = 8.0
    height = 3.0
    
    # Floor
    floor_points = create_floor(width, depth)
    
    # Walls (Counter-clockwise from origin)
    p1 = np.array([0, 0, 0])
    p2 = np.array([width, 0, 0])
    p3 = np.array([width, depth, 0])
    p4 = np.array([0, depth, 0])
    
    w1 = create_wall(p1, p2, height)
    w2 = create_wall(p2, p3, height)
    w3 = create_wall(p3, p4, height)
    w4 = create_wall(p4, p1, height)
    
    all_points = np.vstack((floor_points, w1, w2, w3, w4))
    
    # Add some noise
    noise = np.random.normal(0, 0.02, all_points.shape)
    all_points += noise
    
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)
    
    # Colorize based on height for better visualization
    colors = np.zeros_like(all_points)
    colors[:, 2] = all_points[:, 2] / height  # Blue gradient
    colors[:, 0] = 1.0 - colors[:, 2]         # Red gradient
    pcd.colors = o3d.utility.Vector3dVector(colors)
    
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "layout_dummy.ply")
    o3d.io.write_point_cloud(output_path, pcd)
    print(f"Generated {len(all_points)} points to {output_path}")

if __name__ == "__main__":
    main()
