"""
Generate sample GLB/GLTF data files for REQ-031 testing.

Creates data/mesh_textured/:
  - sample_room.glb   : textured mesh (UV-mapped, embedded texture)
  - sample_room.gltf  : same mesh in GLTF text format + external assets

The mesh is a simple room (10x8x3 m, ROS Z-up) whose walls each map to
a different color region on a single 256x256 texture atlas.

Wall panels are tessellated with a ~0.05 m grid so that any height-slice
with thickness >= 0.1 m always captures vertices regardless of slider position.

Run:
  uv run python scripts/create_sample_glb.py
"""

from pathlib import Path
import numpy as np
import trimesh
import trimesh.visual
from PIL import Image


OUT_DIR = Path("data/mesh_textured")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Grid step: vertices every GRID_STEP metres in each surface dimension.
# With thickness=0.1 m, GRID_STEP <= 0.1 guarantees at least one vertex per slice.
GRID_STEP = 0.05   # 5 cm


# ---------------------------------------------------------------------------
# Texture atlas: 4 colored quadrants + gray cross (floor/ceiling)
# ---------------------------------------------------------------------------

def make_texture_image(size: int = 256) -> Image.Image:
    half = size // 2
    img = np.zeros((size, size, 3), dtype=np.uint8)
    img[:half, :half]     = [220,  80,  80]   # top-left    → red   (front wall)
    img[:half, half:]     = [ 80, 180,  80]   # top-right   → green (right wall)
    img[half:, :half]     = [ 80, 100, 220]   # bottom-left → blue  (back wall)
    img[half:, half:]     = [220, 200,  60]   # bottom-right→ yellow(left wall)
    # center cross → gray (floor & ceiling)
    band = size // 8
    img[half-band:half+band, :] = [160, 160, 160]
    img[:, half-band:half+band] = [160, 160, 160]
    return Image.fromarray(img, "RGB")


# ---------------------------------------------------------------------------
# Grid-tessellated quad builder
# ---------------------------------------------------------------------------

def grid_quad(
    p00: np.ndarray, p10: np.ndarray, p11: np.ndarray, p01: np.ndarray,
    uv00: np.ndarray, uv10: np.ndarray, uv11: np.ndarray, uv01: np.ndarray,
    nu: int, nv: int,
):
    """
    Build a tessellated quad with nu×nv grid cells.

    p00/p10/p11/p01 are the four corners in 3D (shape (3,)).
    uv00..uv01 are the corresponding UV corners (shape (2,)).
    nu, nv: number of divisions along each axis.

    Returns (vertices (N,3), faces (F,3), uvs (N,2)).
    """
    us = np.linspace(0, 1, nu + 1)
    vs = np.linspace(0, 1, nv + 1)

    UU, VV = np.meshgrid(us, vs, indexing='ij')   # (nu+1, nv+1)
    shape = UU.shape

    # Bilinear interpolation for positions
    verts = (
        np.outer((1 - UU.ravel()) * (1 - VV.ravel()), p00) +
        np.outer(      UU.ravel()  * (1 - VV.ravel()), p10) +
        np.outer(      UU.ravel()  *      VV.ravel(),  p11) +
        np.outer((1 - UU.ravel()) *      VV.ravel(),  p01)
    )  # (N, 3)

    # Bilinear interpolation for UVs
    uvs = (
        np.outer((1 - UU.ravel()) * (1 - VV.ravel()), uv00) +
        np.outer(      UU.ravel()  * (1 - VV.ravel()), uv10) +
        np.outer(      UU.ravel()  *      VV.ravel(),  uv11) +
        np.outer((1 - UU.ravel()) *      VV.ravel(),  uv01)
    )  # (N, 2)

    # Build face index grid
    rows, cols = shape
    faces = []
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            b = (i + 1) * (nv + 1) + j
            c = (i + 1) * (nv + 1) + (j + 1)
            d = i * (nv + 1) + (j + 1)
            faces.append([a, b, c])
            faces.append([a, c, d])

    return verts, np.array(faces, dtype=np.int32), uvs.astype(np.float32)


# ---------------------------------------------------------------------------
# Room mesh with dense tessellation
# ---------------------------------------------------------------------------

def build_room_mesh(texture: Image.Image) -> trimesh.Trimesh:
    """
    6-sided box room (10m x 8m x 3m).
    Walls and floor/ceiling are tessellated at GRID_STEP resolution so that
    any height slice ≥ 0.1 m thick always captures vertices.
    """
    material = trimesh.visual.material.PBRMaterial(
        baseColorTexture=texture,
        metallicFactor=0.0,
        roughnessFactor=0.9,
    )

    # UV corner helpers — map a face name to (uv00, uv10, uv11, uv01)
    uv_corners = {
        # center gray band
        "floor":      (np.array([0.375, 0.375]), np.array([0.625, 0.375]),
                       np.array([0.625, 0.625]), np.array([0.375, 0.625])),
        "ceiling":    (np.array([0.375, 0.375]), np.array([0.625, 0.375]),
                       np.array([0.625, 0.625]), np.array([0.375, 0.625])),
        # wall quadrants
        "wall_front": (np.array([0.0, 0.0]), np.array([0.5, 0.0]),
                       np.array([0.5, 0.5]), np.array([0.0, 0.5])),
        "wall_back":  (np.array([0.0, 0.5]), np.array([0.5, 0.5]),
                       np.array([0.5, 1.0]), np.array([0.0, 1.0])),
        "wall_right": (np.array([0.5, 0.0]), np.array([1.0, 0.0]),
                       np.array([1.0, 0.5]), np.array([0.5, 0.5])),
        "wall_left":  (np.array([0.5, 0.5]), np.array([1.0, 0.5]),
                       np.array([1.0, 1.0]), np.array([0.5, 1.0])),
    }

    # Room dimensions
    W, D, H = 10.0, 8.0, 3.0   # width (x), depth (y), height (z)
    g = GRID_STEP

    # Each panel: (name, p00, p10, p11, p01, nu, nv)
    panels = [
        # floor: z=0, spans x=[0,W], y=[0,D]
        ("floor",
         [0, 0, 0], [W, 0, 0], [W, D, 0], [0, D, 0],
         int(W / g), int(D / g)),
        # ceiling: z=H, reversed winding (normals face down)
        ("ceiling",
         [0, 0, H], [0, D, H], [W, D, H], [W, 0, H],
         int(D / g), int(W / g)),
        # front wall: y=0, spans x=[0,W], z=[0,H]
        ("wall_front",
         [0, 0, 0], [W, 0, 0], [W, 0, H], [0, 0, H],
         int(W / g), int(H / g)),
        # back wall: y=D, reversed winding
        ("wall_back",
         [W, D, 0], [0, D, 0], [0, D, H], [W, D, H],
         int(W / g), int(H / g)),
        # right wall: x=W, spans y=[0,D], z=[0,H]
        ("wall_right",
         [W, 0, 0], [W, D, 0], [W, D, H], [W, 0, H],
         int(D / g), int(H / g)),
        # left wall: x=0, reversed winding
        ("wall_left",
         [0, D, 0], [0, 0, 0], [0, 0, H], [0, D, H],
         int(D / g), int(H / g)),
    ]

    all_verts, all_faces, all_uvs = [], [], []
    offset = 0
    for name, p00, p10, p11, p01, nu, nv in panels:
        uvc = uv_corners[name]
        v, f, u = grid_quad(
            np.array(p00, dtype=np.float64),
            np.array(p10, dtype=np.float64),
            np.array(p11, dtype=np.float64),
            np.array(p01, dtype=np.float64),
            uvc[0], uvc[1], uvc[2], uvc[3],
            nu, nv,
        )
        all_verts.append(v)
        all_faces.append(f + offset)
        all_uvs.append(u)
        offset += len(v)

    vertices = np.vstack(all_verts)
    faces    = np.vstack(all_faces)
    uvs      = np.vstack(all_uvs)

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    mesh.visual = trimesh.visual.TextureVisuals(uv=uvs, material=material)
    return mesh


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Building texture atlas...")
    texture = make_texture_image(256)

    print(f"Building room mesh (10m x 8m x 3m, ROS Z-up, grid_step={GRID_STEP}m)...")
    mesh = build_room_mesh(texture)

    print(f"  Vertices : {len(mesh.vertices)}")
    print(f"  Faces    : {len(mesh.faces)}")
    print(f"  UV shape : {mesh.visual.uv.shape}")

    # Verify density: every 0.1 m slice should capture vertices
    pts = np.asarray(mesh.vertices)
    zvals = np.unique(np.round(pts[:, 2], 4))
    print(f"  Z levels : {len(zvals)}  (range {zvals[0]:.2f}–{zvals[-1]:.2f} m)")
    dz_max = float(np.diff(zvals).max()) if len(zvals) > 1 else float('inf')
    print(f"  Max z gap: {dz_max:.4f} m  (slice thickness=0.1 → needs <= 0.1)")
    assert dz_max <= 0.1, f"Z gap {dz_max:.4f} m exceeds 0.1 m slice thickness"

    # --- GLB ---
    glb_path = OUT_DIR / "sample_room.glb"
    glb_data = trimesh.exchange.gltf.export_glb(
        trimesh.Scene(geometry={"room": mesh})
    )
    glb_path.write_bytes(glb_data)
    print(f"\nSaved GLB  : {glb_path}  ({glb_path.stat().st_size // 1024} KB)")

    # --- GLTF + external assets ---
    gltf_dir = OUT_DIR / "sample_room_gltf"
    gltf_dir.mkdir(exist_ok=True)
    scene_obj = trimesh.Scene(geometry={"room": mesh})
    gltf_dict = trimesh.exchange.gltf.export_gltf(scene_obj, merge_buffers=False)
    for filename, data in gltf_dict.items():
        (gltf_dir / filename).write_bytes(data)
    gltf_path = gltf_dir / "model.gltf"
    print(f"Saved GLTF : {gltf_path} + {len(gltf_dict)-1} external asset(s)")
    for f in gltf_dict.keys():
        path = gltf_dir / f
        print(f"  {path.name}  ({path.stat().st_size // 1024} KB)")

    # --- Verify reload ---
    print("\nVerifying GLB reload with trimesh...")
    loaded = trimesh.load(str(glb_path))
    if isinstance(loaded, trimesh.Scene):
        for name, geom in loaded.geometry.items():
            if isinstance(geom, trimesh.Trimesh):
                colored = geom.visual.to_color()
                vc = colored.vertex_colors
                pts2 = np.asarray(geom.vertices)
                print(f"  Mesh '{name}': {len(geom.vertices)} verts, "
                      f"vertex_colors shape after bake: {vc.shape}")
                for test_z in [0.5, 1.0, 1.5, 2.0, 2.5]:
                    cnt = int(((pts2[:, 2] >= test_z - 0.05) &
                               (pts2[:, 2] <= test_z + 0.05)).sum())
                    print(f"    slice z={test_z:.1f} (±0.05m): {cnt} verts")
    else:
        colored = loaded.visual.to_color()
        print(f"  Mesh: {len(loaded.vertices)} verts, "
              f"vertex_colors shape: {colored.vertex_colors.shape}")

    print("\nDone. Files written to data/mesh_textured/")


if __name__ == "__main__":
    main()
