import open3d as o3d
import os
import sys

def main():
    file_path = "data/layout_dummy.ply"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        sys.exit(1)
        
    print(f"Loading {file_path}...")
    try:
        pcd = o3d.io.read_point_cloud(file_path)
        print(f"Successfully loaded point cloud.")
        print(f"Points: {len(pcd.points)}")
        print(f"Bounds: {pcd.get_min_bound()} - {pcd.get_max_bound()}")
        
        # Check colors
        if pcd.has_colors():
            print("Point cloud has colors.")
        else:
            print("Point cloud has no colors.")
            
    except Exception as e:
        print(f"Failed to load point cloud: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
