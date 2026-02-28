import unittest
from dataclasses import asdict
from src.model.data import (
    Point2D, Wall, Room, Object, CustomPolygon, ProjectData, MapMetadata,
)

class TestDataModel(unittest.TestCase):
    def test_point2d(self):
        p = Point2D(1.0, 2.0)
        d = asdict(p)
        self.assertEqual(d, {"x": 1.0, "y": 2.0})
        p2 = Point2D(**d)
        self.assertEqual(p.x, p2.x)
        self.assertEqual(p.y, p2.y)

    def test_wall(self):
        w = Wall(Point2D(0,0), Point2D(10,0))
        d = w.to_dict()
        w2 = Wall.from_dict(d)
        self.assertEqual(w.start.x, w2.start.x)

    def test_room(self):
        points = [Point2D(0,0), Point2D(10,0), Point2D(10,10)]
        r = Room(points=points, category="bedroom", room_type="master")
        d = r.to_dict()
        r2 = Room.from_dict(d)
        self.assertEqual(r.room_type, r2.room_type)
        self.assertEqual(len(r2.points), 3)

    def test_project_data(self):
        pd = ProjectData()
        pd.walls.append(Wall(Point2D(0,0), Point2D(1,1)))
        d = pd.to_dict()
        pd2 = ProjectData.from_dict(d)
        self.assertEqual(len(pd2.walls), 1)

    def test_object_to_dict(self):
        obj = Object(center=Point2D(1.0, 2.0), width=3.0, height=4.0, rotation=45.0, object_type="chair")
        d = obj.to_dict()
        self.assertIn("center", d)
        self.assertEqual(d["center"]["x"], 1.0)
        self.assertEqual(d["center"]["y"], 2.0)
        self.assertEqual(d["width"], 3.0)
        self.assertEqual(d["height"], 4.0)
        self.assertEqual(d["rotation"], 45.0)
        self.assertEqual(d["object_type"], "chair")

    def test_object_roundtrip(self):
        obj = Object(center=Point2D(5.0, 6.0), width=2.0, height=3.0, rotation=90.0, object_type="table")
        d = obj.to_dict()
        obj2 = Object.from_dict(d)
        self.assertEqual(obj2.center.x, 5.0)
        self.assertEqual(obj2.center.y, 6.0)
        self.assertEqual(obj2.width, 2.0)
        self.assertEqual(obj2.height, 3.0)
        self.assertEqual(obj2.rotation, 90.0)
        self.assertEqual(obj2.object_type, "table")

    def test_custom_polygon_to_dict(self):
        cp = CustomPolygon(
            points=[Point2D(0, 0), Point2D(10, 0), Point2D(10, 10)],
            polygon_type="cleaning_zone"
        )
        d = cp.to_dict()
        self.assertIn("points", d)
        self.assertEqual(len(d["points"]), 3)
        self.assertEqual(d["polygon_type"], "cleaning_zone")

    def test_custom_polygon_roundtrip(self):
        cp = CustomPolygon(
            points=[Point2D(1, 2), Point2D(3, 4), Point2D(5, 6)],
            polygon_type="complex_area"
        )
        d = cp.to_dict()
        cp2 = CustomPolygon.from_dict(d)
        self.assertEqual(cp2.polygon_type, "complex_area")
        self.assertEqual(len(cp2.points), 3)
        self.assertEqual(cp2.points[0].x, 1.0)
        self.assertEqual(cp2.points[2].y, 6.0)

    def test_project_data_with_objects_and_custom_polygons(self):
        pd = ProjectData()
        pd.walls.append(Wall(Point2D(0, 0), Point2D(1, 1)))
        pd.objects.append(Object(center=Point2D(2, 3), object_type="sofa"))
        pd.custom_polygons.append(
            CustomPolygon(points=[Point2D(0,0), Point2D(5,0), Point2D(5,5)], polygon_type="zone_a")
        )
        d = pd.to_dict()

        # Verify serialized
        self.assertEqual(len(d["objects"]), 1)
        self.assertEqual(len(d["custom_polygons"]), 1)

        # Roundtrip
        pd2 = ProjectData.from_dict(d)
        self.assertEqual(len(pd2.walls), 1)
        self.assertEqual(len(pd2.objects), 1)
        self.assertEqual(pd2.objects[0].object_type, "sofa")
        self.assertEqual(len(pd2.custom_polygons), 1)
        self.assertEqual(pd2.custom_polygons[0].polygon_type, "zone_a")

    def test_project_data_backwards_compat_no_custom_polygons(self):
        """Old JSON without custom_polygons should deserialize without error."""
        d = {
            "version": "1.0",
            "walls": [],
            "rooms": [],
            "objects": [],
        }
        pd = ProjectData.from_dict(d)
        self.assertEqual(pd.custom_polygons, [])


class TestMapMetadata(unittest.TestCase):
    """Tests for MapMetadata serialization/deserialization."""

    def _make_metadata(self):
        return MapMetadata(
            image_path="maps/floor1.png",
            image_path_absolute="/home/user/project/maps/floor1.png",
            resolution=0.05,
            origin_x=-5.0,
            origin_y=-3.0,
            origin_yaw=1.57,
            negate=1,
            occupied_thresh=0.70,
            free_thresh=0.20,
            image_width=200,
            image_height=150,
        )

    def test_to_dict_contains_all_fields(self):
        meta = self._make_metadata()
        d = meta.to_dict()

        expected_keys = {
            "image_path", "resolution",
            "origin_x", "origin_y", "origin_yaw", "negate",
            "occupied_thresh", "free_thresh", "image_width", "image_height",
        }
        self.assertEqual(set(d.keys()), expected_keys)
        self.assertNotIn("image_path_absolute", d)

    def test_roundtrip(self):
        """to_dict then from_dict should preserve every field except image_path_absolute."""
        original = self._make_metadata()
        d = original.to_dict()
        # image_path_absolute is runtime-only — not serialized
        self.assertNotIn("image_path_absolute", d)
        restored = MapMetadata.from_dict(d)

        self.assertEqual(restored.image_path, original.image_path)
        # image_path_absolute is empty after roundtrip (not saved to disk)
        self.assertEqual(restored.image_path_absolute, "")
        self.assertAlmostEqual(restored.resolution, original.resolution)
        self.assertAlmostEqual(restored.origin_x, original.origin_x)
        self.assertAlmostEqual(restored.origin_y, original.origin_y)
        self.assertAlmostEqual(restored.origin_yaw, original.origin_yaw)
        self.assertEqual(restored.negate, original.negate)
        self.assertAlmostEqual(restored.occupied_thresh, original.occupied_thresh)
        self.assertAlmostEqual(restored.free_thresh, original.free_thresh)
        self.assertEqual(restored.image_width, original.image_width)
        self.assertEqual(restored.image_height, original.image_height)

    def test_from_dict_with_defaults(self):
        """from_dict on an empty dict should use sensible defaults."""
        meta = MapMetadata.from_dict({})
        self.assertEqual(meta.image_path, "")
        self.assertAlmostEqual(meta.resolution, 0.05)
        self.assertAlmostEqual(meta.origin_x, 0.0)
        self.assertAlmostEqual(meta.origin_y, 0.0)
        self.assertEqual(meta.negate, 0)

    def test_from_dict_reads_legacy_absolute_path(self):
        """Legacy files that include image_path_absolute should still load it into memory."""
        d = {
            "image_path": "maps/floor1.png",
            "image_path_absolute": "/home/user/project/maps/floor1.png",
            "resolution": 0.05,
        }
        meta = MapMetadata.from_dict(d)
        self.assertEqual(meta.image_path, "maps/floor1.png")
        self.assertEqual(meta.image_path_absolute, "/home/user/project/maps/floor1.png")


class TestProjectDataWithMapMetadata(unittest.TestCase):
    """Tests for ProjectData v3.0 map_metadata integration."""

    def test_project_data_v3_with_map_metadata(self):
        """ProjectData with map_metadata set should roundtrip correctly."""
        meta = MapMetadata(
            image_path="data/map.png",
            image_path_absolute="/abs/data/map.png",
            resolution=0.05,
            origin_x=-5.0,
            origin_y=-5.0,
            image_width=200,
            image_height=200,
        )
        pd = ProjectData()
        pd.map_metadata = meta
        pd.walls.append(Wall(start=Point2D(0, 0), end=Point2D(1, 1)))

        d = pd.to_dict()

        # map_metadata should be present in the serialized dict
        self.assertIn("map_metadata", d)
        self.assertEqual(d["map_metadata"]["image_path"], "data/map.png")
        self.assertEqual(d["map_metadata"]["image_width"], 200)
        self.assertEqual(d["version"], "3.0")

        # Roundtrip
        pd2 = ProjectData.from_dict(d)
        self.assertIsNotNone(pd2.map_metadata)
        self.assertEqual(pd2.map_metadata.image_path, "data/map.png")
        self.assertAlmostEqual(pd2.map_metadata.resolution, 0.05)
        self.assertAlmostEqual(pd2.map_metadata.origin_x, -5.0)
        self.assertEqual(pd2.map_metadata.image_width, 200)
        self.assertEqual(len(pd2.walls), 1)

    def test_project_data_without_map_metadata(self):
        """ProjectData with map_metadata=None should not include it in dict."""
        pd = ProjectData()
        pd.map_metadata = None

        d = pd.to_dict()
        self.assertNotIn("map_metadata", d)

    def test_v2_backward_compatibility_no_map_metadata(self):
        """A v2.0 dict with coordinate_system but no map_metadata should deserialize with map_metadata=None."""
        from src.core.coordinate_system import CoordinateSystem
        d = {
            "version": "2.0",
            "coordinate_system": CoordinateSystem.ros().to_dict(),
            "walls": [],
            "rooms": [],
            "objects": [],
            "custom_polygons": [],
        }
        pd = ProjectData.from_dict(d)
        self.assertIsNone(pd.map_metadata)
        self.assertEqual(pd.version, "2.0")

    def test_v1_backward_compatibility_no_map_metadata(self):
        """A v1.0 dict (no coordinate_system, no map_metadata) should work."""
        d = {
            "version": "1.0",
            "walls": [],
            "rooms": [],
        }
        pd = ProjectData.from_dict(d)
        self.assertIsNone(pd.map_metadata)
        self.assertEqual(pd.version, "1.0")


if __name__ == "__main__":
    unittest.main()
