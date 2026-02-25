"""ROS2 occupancy grid map loader.

Loads ROS2 map_server compatible occupancy grid maps (YAML + image).
"""

import os
from typing import Optional, Tuple

import numpy as np
import yaml
from PyQt6.QtGui import QImage

from src.model.data import MapMetadata


class MapLoader:
    """Loads ROS2 map_server compatible occupancy grid maps."""

    @staticmethod
    def parse_yaml(yaml_path: str) -> MapMetadata:
        """Parse a ROS2 map YAML file and return MapMetadata.

        Args:
            yaml_path: Absolute path to the .yaml file.

        Returns:
            MapMetadata with parsed values.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValueError: If required fields are missing or invalid.
        """
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Map YAML not found: {yaml_path}")

        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        if data is None:
            raise ValueError(f"Empty YAML file: {yaml_path}")

        # Resolve image path relative to YAML location
        yaml_dir = os.path.dirname(os.path.abspath(yaml_path))
        image_rel = data.get("image", "")
        if not image_rel:
            raise ValueError("Missing 'image' field in map YAML")
        image_abs = os.path.normpath(os.path.join(yaml_dir, image_rel))

        # Parse origin: [x, y, yaw]
        origin = data.get("origin", [0.0, 0.0, 0.0])
        if not isinstance(origin, list) or len(origin) < 2:
            raise ValueError(f"Invalid origin in YAML: {origin}")

        resolution = data.get("resolution", 0.05)
        if resolution <= 0:
            raise ValueError(f"Invalid resolution: {resolution}")

        return MapMetadata(
            image_path=image_rel,
            image_path_absolute=image_abs,
            resolution=float(resolution),
            origin_x=float(origin[0]),
            origin_y=float(origin[1]),
            origin_yaw=float(origin[2]) if len(origin) > 2 else 0.0,
            negate=int(data.get("negate", 0)),
            occupied_thresh=float(data.get("occupied_thresh", 0.65)),
            free_thresh=float(data.get("free_thresh", 0.196)),
        )

    @staticmethod
    def load_image(image_path: str, metadata: MapMetadata) -> np.ndarray:
        """Load occupancy grid image as a grayscale numpy array.

        Uses QImage for format support (PGM, PNG, etc.) without extra dependencies.
        Applies negate if specified in metadata.

        Args:
            image_path: Absolute path to the image file.
            metadata: MapMetadata (negate flag is applied, image_width/height are set).

        Returns:
            numpy array of shape (H, W), dtype uint8.

        Raises:
            FileNotFoundError: If the image file does not exist.
            ValueError: If the image cannot be loaded.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Map image not found: {image_path}")

        q_image = QImage(image_path)
        if q_image.isNull():
            raise ValueError(f"Cannot load image: {image_path}")

        # Convert to grayscale
        q_image = q_image.convertToFormat(QImage.Format.Format_Grayscale8)

        width = q_image.width()
        height = q_image.height()
        bytes_per_line = q_image.bytesPerLine()

        # Convert QImage to numpy array
        ptr = q_image.bits()
        ptr.setsize(height * bytes_per_line)
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape(height, bytes_per_line)
        # Trim padding bytes (bytesPerLine may be > width for alignment)
        arr = arr[:, :width].copy()

        if metadata.negate:
            arr = 255 - arr

        # Store dimensions in metadata
        metadata.image_height = height
        metadata.image_width = width

        return arr

    @staticmethod
    def compute_bounds(metadata: MapMetadata) -> Tuple[float, float, float, float]:
        """Compute world-coordinate bounds from map metadata.

        ROS2 origin is the world position of the lower-left pixel.
        Image row 0 is the TOP of the image (standard raster order),
        which corresponds to world max_y.

        Returns:
            (min_x, min_y, max_x, max_y) in world meters.
        """
        min_x = metadata.origin_x
        min_y = metadata.origin_y
        max_x = min_x + metadata.image_width * metadata.resolution
        max_y = min_y + metadata.image_height * metadata.resolution
        return (min_x, min_y, max_x, max_y)

    @staticmethod
    def compute_scale(metadata: MapMetadata) -> float:
        """Compute pixels-per-meter scale from resolution.

        Returns:
            Pixels per meter (1.0 / resolution).
        """
        return 1.0 / metadata.resolution

    @staticmethod
    def classify_pixels(image_data: np.ndarray, metadata: MapMetadata) -> np.ndarray:
        """Classify pixels into occupied/free/unknown.

        ROS trinary mode:
            occ_prob = (255 - pixel_value) / 255.0
            occupied: occ_prob > occupied_thresh
            free:     occ_prob < free_thresh
            unknown:  everything else

        Args:
            image_data: Grayscale image array (H, W), uint8.
            metadata: MapMetadata with threshold values.

        Returns:
            Array of same shape with values: 0=free, 1=occupied, 2=unknown.
        """
        # Convert pixel value thresholds
        # occupied: pixel < (1 - occupied_thresh) * 255
        # free: pixel > (1 - free_thresh) * 255
        occ_pixel_max = (1.0 - metadata.occupied_thresh) * 255.0
        free_pixel_min = (1.0 - metadata.free_thresh) * 255.0

        result = np.full_like(image_data, 2, dtype=np.uint8)  # default: unknown
        result[image_data <= occ_pixel_max] = 1  # occupied
        result[image_data >= free_pixel_min] = 0  # free
        return result

    @staticmethod
    def find_yaml_for_image(image_path: str) -> Optional[str]:
        """Look for a .yaml file in the same directory as the image.

        Tries: same basename with .yaml/.yml extension, then map.yaml/map.yml.

        Args:
            image_path: Absolute path to the image file.

        Returns:
            Path to the YAML file if found, None otherwise.
        """
        directory = os.path.dirname(image_path)
        basename = os.path.splitext(os.path.basename(image_path))[0]

        candidates = [
            os.path.join(directory, basename + ".yaml"),
            os.path.join(directory, basename + ".yml"),
            os.path.join(directory, "map.yaml"),
            os.path.join(directory, "map.yml"),
        ]

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return None

    @staticmethod
    def make_relative_path(image_abs: str, project_path: str) -> str:
        """Compute the image path relative to the project file location.

        Args:
            image_abs: Absolute path to the map image.
            project_path: Absolute path to the project JSON file.

        Returns:
            Relative path string.
        """
        project_dir = os.path.dirname(os.path.abspath(project_path))
        return os.path.relpath(image_abs, project_dir)
