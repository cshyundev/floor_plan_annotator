import numpy as np
import open3d as o3d
from src.core.processor import SliceEngine
import os

def test_slicing():
    # Create synthetic data
    # Floor: 10x10 at z=0
    # Wall: 10m long, 3m high at x=5
    
    points = []
    # Floor
    for x in np.linspace(0, 10, 100):
        for y in np.linspace(0, 10, 100):
            points.append([x, y, 0])
            
    # Wall (Vertical plane at x=5)
    for y in np.linspace(0, 10, 100):
        for z in np.linspace(0, 3, 30):
            points.append([5, y, z])
            
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.array(points))
    
    engine = SliceEngine()
    engine.load_data(pcd)
    
    # Test 1: Slice at z=1.5 (should only see the wall)
    sliced_pts, _ = engine.slice_at_height(1.5, thickness=0.2)
    print(f"Slice at 1.5m points: {len(sliced_pts)}")
    
    # Should be roughly one strip of the wall
    # Wall has 100 * 30 = 3000 points over 3m.
    # 0.2m thickness is ~ 200 points.
    assert len(sliced_pts) > 0, "Slice at wall height should not be empty"
    
    # Check bounds of slice
    min_x = sliced_pts[:, 0].min()
    max_x = sliced_pts[:, 0].max()
    print(f"Slice X range: {min_x} - {max_x}")
    assert 4.9 < min_x and max_x < 5.1, "Slice should be at x=5"
    
    # Test 2: Project to image
    img, bounds, scale = engine.project_to_image(sliced_pts, pixel_size=0.05)
    print(f"Projected Image Size: {img.shape}")
    print(f"Bounds: {bounds}")
    
    # Save debug image
    try:
        from PIL import Image
        pil_img = Image.fromarray(img)
        pil_img.save("debug_slice.png")
        print("Saved debug_slice.png")
    except ImportError:
        print("PIL not installed, skipping image save")

if __name__ == "__main__":
    test_slicing()
