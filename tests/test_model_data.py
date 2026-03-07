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

        # Verify v1.0 schema structure
        self.assertEqual(len(d["objects"]), 1)
        self.assertEqual(len(d["zones"]), 1)

        # Roundtrip
        pd2 = ProjectData.from_dict(d)
        self.assertEqual(len(pd2.walls), 1)
        self.assertEqual(len(pd2.objects), 1)
        self.assertEqual(pd2.objects[0].object_type, "sofa")
        self.assertEqual(len(pd2.custom_polygons), 1)
        self.assertEqual(pd2.custom_polygons[0].polygon_type, "zone_a")



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


class TestProjectDataSource(unittest.TestCase):
    """Tests for ProjectData source (map_metadata) serialization."""

    def test_source_from_map_metadata(self):
        """ProjectData with map_metadata produces 'source' in v1.0 output."""
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

        # v1.0 schema: source block instead of map_metadata
        self.assertIn("source", d)
        self.assertEqual(d["source"]["file_name"], "map.png")
        self.assertEqual(d["version"], "1.0")

        # Roundtrip
        pd2 = ProjectData.from_dict(d)
        self.assertIsNotNone(pd2.map_metadata)
        self.assertEqual(pd2.map_metadata.image_path, "map.png")
        self.assertEqual(len(pd2.walls), 1)

    def test_source_occupancy_grid(self):
        """Occupancy grid data_type includes occupancy_grid sub-object in source."""
        meta = MapMetadata(
            image_path="floor.pgm",
            resolution=0.05,
            origin_x=-10.0,
            origin_y=-10.0,
            origin_yaw=0.0,
            negate=0,
            occupied_thresh=0.65,
            free_thresh=0.196,
        )
        pd = ProjectData()
        pd.map_metadata = meta
        pd.data_type = "occupancy_grid"

        d = pd.to_dict()
        self.assertIn("occupancy_grid", d["source"])
        occ = d["source"]["occupancy_grid"]
        self.assertAlmostEqual(occ["resolution"], 0.05)
        self.assertEqual(occ["origin"], [-10.0, -10.0, 0.0])

        # Roundtrip
        pd2 = ProjectData.from_dict(d)
        self.assertIsNotNone(pd2.map_metadata)
        self.assertAlmostEqual(pd2.map_metadata.resolution, 0.05)
        self.assertAlmostEqual(pd2.map_metadata.origin_x, -10.0)

    def test_no_map_metadata_no_source(self):
        """ProjectData with map_metadata=None should not include source."""
        pd = ProjectData()
        pd.map_metadata = None

        d = pd.to_dict()
        self.assertNotIn("source", d)



class TestV1SchemaFormat(unittest.TestCase):
    """Tests for the v1.0 schema output format."""

    def test_to_dict_structure(self):
        """to_dict produces correct top-level v1.0 structure."""
        pd = ProjectData()
        pd.walls.append(Wall(start=Point2D(1, 2), end=Point2D(3, 4)))
        pd.rooms.append(Room(id="r1", points=[Point2D(0,0), Point2D(1,0), Point2D(1,1)], room_type="bedroom"))
        pd.objects.append(Object(id="o1", center=Point2D(5, 5), width=2, height=1, rotation=0, object_type="furniture"))
        pd.custom_polygons.append(CustomPolygon(id="z1", points=[Point2D(0,0), Point2D(1,0), Point2D(1,1)], polygon_type="no_go"))

        d = pd.to_dict()

        self.assertEqual(d["version"], "1.0")
        self.assertEqual(d["data_type"], "point_cloud")
        self.assertEqual(d["coordinate_system"], "ros")
        self.assertIn("layout", d)
        self.assertIn("walls", d["layout"])
        self.assertIn("rooms", d["layout"])
        self.assertIn("objects", d)
        self.assertIn("zones", d)

    def test_wall_3d_serialization(self):
        """Walls serialize as [[x,y,z], [x,y,z]] with z=floor_level."""
        pd = ProjectData()
        pd.walls.append(Wall(start=Point2D(1.0, 2.0), end=Point2D(3.0, 4.0)))

        d = pd.to_dict()
        walls = d["layout"]["walls"]
        self.assertEqual(len(walls), 1)
        # ROS: make_3d_point(h, v, height) → [h, v, height]
        self.assertEqual(walls[0], [[1.0, 2.0, 0.0], [3.0, 4.0, 0.0]])

    def test_wall_3d_with_floor_level(self):
        """Walls with non-zero floor_level use it as z."""
        from src.core.coordinate_system import CoordinateSystem
        pd = ProjectData()
        cs = CoordinateSystem.ros()
        cs.floor_level = 1.5
        pd.coordinate_system = cs
        pd.walls.append(Wall(start=Point2D(0, 0), end=Point2D(1, 1)))

        d = pd.to_dict()
        self.assertEqual(d["floor_level"], 1.5)
        self.assertEqual(d["layout"]["walls"][0], [[0, 0, 1.5], [1, 1, 1.5]])

    def test_room_serialization(self):
        """Rooms serialize with id, type, and Point3D array."""
        pd = ProjectData()
        pd.rooms.append(Room(id="0", points=[Point2D(0,0), Point2D(1,0), Point2D(1,1)], room_type="kitchen"))

        d = pd.to_dict()
        rooms = d["layout"]["rooms"]
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]["id"], "0")
        self.assertEqual(rooms[0]["type"], "kitchen")
        self.assertEqual(rooms[0]["points"], [[0, 0, 0.0], [1, 0, 0.0], [1, 1, 0.0]])

    def test_object_obb_serialization(self):
        """Objects serialize as OBB with center, extent, quaternion."""
        pd = ProjectData()
        pd.objects.append(Object(
            id="0", center=Point2D(5.0, 3.0),
            width=1.2, height=0.8, rotation=0.0,
            object_type="furniture",
            z_min=0.0, z_max=0.75,
        ))

        d = pd.to_dict()
        obj = d["objects"][0]
        self.assertEqual(obj["id"], "0")
        self.assertEqual(obj["type"], "furniture")
        # center: [5.0, 3.0, 0.375] (midpoint of z_min=0 and z_max=0.75)
        self.assertAlmostEqual(obj["center"][0], 5.0)
        self.assertAlmostEqual(obj["center"][1], 3.0)
        self.assertAlmostEqual(obj["center"][2], 0.375)
        # extent: [width, height, depth]
        self.assertEqual(obj["extent"], [1.2, 0.8, 0.75])
        # rotation: identity quaternion for 0 degrees
        self.assertAlmostEqual(obj["rotation"][0], 1.0)
        self.assertAlmostEqual(obj["rotation"][1], 0.0)
        self.assertAlmostEqual(obj["rotation"][2], 0.0)
        self.assertAlmostEqual(obj["rotation"][3], 0.0)

    def test_zone_serialization(self):
        """CustomPolygons serialize as zones."""
        pd = ProjectData()
        pd.custom_polygons.append(CustomPolygon(
            id="0", points=[Point2D(0,0), Point2D(2,0), Point2D(2,1.5)], polygon_type="no_go"
        ))

        d = pd.to_dict()
        zones = d["zones"]
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0]["id"], "0")
        self.assertEqual(zones[0]["type"], "no_go")
        self.assertEqual(len(zones[0]["points"]), 3)

    def test_object_rotation_roundtrip(self):
        """degrees → quaternion → degrees roundtrip preserves rotation."""
        from src.model.data import _degrees_to_quaternion, _quaternion_to_degrees
        from src.core.coordinate_system import CoordinateSystem

        for cs in [CoordinateSystem.ros(), CoordinateSystem.opencv(), CoordinateSystem.opengl()]:
            for deg in [0, 45, 90, 180, -30, 270]:
                quat = _degrees_to_quaternion(deg, cs)
                restored = _quaternion_to_degrees(quat, cs)
                self.assertAlmostEqual(restored, deg, places=5,
                    msg=f"Failed for {cs.to_preset_name()} at {deg}°")

    def test_full_roundtrip(self):
        """to_dict → from_dict preserves all data."""
        pd = ProjectData()
        pd.data_type = "point_cloud"
        pd.created_at = "2026-03-01T12:00:00+00:00"
        pd.modified_at = "2026-03-01T15:00:00+00:00"
        pd.walls.append(Wall(start=Point2D(1.0, 2.0), end=Point2D(3.0, 4.0)))
        pd.rooms.append(Room(id="r0", points=[
            Point2D(0, 0), Point2D(5, 0), Point2D(5, 5), Point2D(0, 5)
        ], room_type="bedroom"))
        pd.objects.append(Object(
            id="o0", center=Point2D(2.5, 2.5),
            width=1.0, height=0.5, rotation=45.0,
            object_type="furniture", z_min=0.0, z_max=0.8,
        ))
        pd.custom_polygons.append(CustomPolygon(
            id="z0", points=[Point2D(0, 0), Point2D(1, 0), Point2D(1, 1)],
            polygon_type="caution",
        ))

        d = pd.to_dict()
        pd2 = ProjectData.from_dict(d)

        self.assertEqual(pd2.version, "1.0")
        self.assertEqual(pd2.data_type, "point_cloud")
        self.assertEqual(pd2.created_at, "2026-03-01T12:00:00+00:00")
        self.assertEqual(pd2.modified_at, "2026-03-01T15:00:00+00:00")

        # Walls
        self.assertEqual(len(pd2.walls), 1)
        self.assertAlmostEqual(pd2.walls[0].start.x, 1.0)
        self.assertAlmostEqual(pd2.walls[0].end.y, 4.0)

        # Rooms
        self.assertEqual(len(pd2.rooms), 1)
        self.assertEqual(pd2.rooms[0].id, "r0")
        self.assertEqual(pd2.rooms[0].room_type, "Bedroom")
        self.assertEqual(len(pd2.rooms[0].points), 4)

        # Objects
        self.assertEqual(len(pd2.objects), 1)
        self.assertAlmostEqual(pd2.objects[0].center.x, 2.5)
        self.assertAlmostEqual(pd2.objects[0].width, 1.0)
        self.assertAlmostEqual(pd2.objects[0].rotation, 45.0, places=3)
        self.assertEqual(pd2.objects[0].object_type, "Furniture")

        # Zones → custom_polygons
        self.assertEqual(len(pd2.custom_polygons), 1)
        self.assertEqual(pd2.custom_polygons[0].id, "z0")
        self.assertEqual(pd2.custom_polygons[0].polygon_type, "caution")

    def test_load_example_json(self):
        """Load schemas/example.json and verify it parses correctly."""
        import json
        import os
        example_path = os.path.join(os.path.dirname(__file__), "..", "schemas", "example.json")
        with open(example_path) as f:
            data = json.load(f)

        pd = ProjectData.from_dict(data)

        self.assertEqual(pd.version, "1.0")
        self.assertEqual(pd.data_type, "point_cloud")
        self.assertEqual(len(pd.walls), 4)
        self.assertEqual(len(pd.rooms), 1)
        self.assertEqual(pd.rooms[0].room_type, "Bedroom")
        self.assertEqual(len(pd.objects), 2)
        self.assertEqual(pd.objects[0].object_type, "Furniture")
        self.assertEqual(len(pd.custom_polygons), 2)
        self.assertEqual(pd.custom_polygons[0].polygon_type, "no_go")

    def test_timestamps_optional(self):
        """created_at / modified_at are optional."""
        pd = ProjectData()
        d = pd.to_dict()
        self.assertNotIn("created_at", d)
        self.assertNotIn("modified_at", d)

    def test_floor_level_omitted_when_zero(self):
        """floor_level is not included when 0.0."""
        pd = ProjectData()
        d = pd.to_dict()
        self.assertNotIn("floor_level", d)

    def test_opencv_coordinate_system_roundtrip(self):
        """OpenCV coordinate system serializes as string and roundtrips."""
        from src.core.coordinate_system import CoordinateSystem
        pd = ProjectData()
        pd.coordinate_system = CoordinateSystem.opencv()
        pd.walls.append(Wall(start=Point2D(1, 2), end=Point2D(3, 4)))

        d = pd.to_dict()
        self.assertEqual(d["coordinate_system"], "opencv")

        pd2 = ProjectData.from_dict(d)
        self.assertEqual(pd2.coordinate_system.up_axis, 1)
        self.assertEqual(pd2.coordinate_system.up_direction, -1)
        self.assertEqual(pd2.coordinate_system.floor_axes, (0, 2))


class TestSchemaValidation(unittest.TestCase):
    """Tests for JSON schema validation in ProjectIO.load_project."""

    def test_invalid_version_rejected(self):
        """Version mismatch raises ValidationError."""
        import json, tempfile, os
        from jsonschema import ValidationError
        from src.core.io import ProjectIO

        data = {
            "version": "99.0",
            "data_type": "point_cloud",
            "coordinate_system": "ros",
            "layout": {"walls": [], "rooms": []},
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValidationError):
                ProjectIO.load_project(path)
        finally:
            os.unlink(path)

    def test_missing_required_field_rejected(self):
        """Missing required 'layout' key raises ValidationError."""
        import json, tempfile, os
        from jsonschema import ValidationError
        from src.core.io import ProjectIO

        data = {
            "version": "1.0",
            "data_type": "point_cloud",
            "coordinate_system": "ros",
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValidationError):
                ProjectIO.load_project(path)
        finally:
            os.unlink(path)

    def test_invalid_coordinate_system_rejected(self):
        """Invalid coordinate_system enum raises ValidationError."""
        import json, tempfile, os
        from jsonschema import ValidationError
        from src.core.io import ProjectIO

        data = {
            "version": "1.0",
            "data_type": "point_cloud",
            "coordinate_system": "unity",
            "layout": {"walls": [], "rooms": []},
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            with self.assertRaises(ValidationError):
                ProjectIO.load_project(path)
        finally:
            os.unlink(path)

    def test_valid_example_passes(self):
        """schemas/example.json passes schema validation."""
        import os
        from src.core.io import ProjectIO

        example_path = os.path.join(os.path.dirname(__file__), "..", "schemas", "example.json")
        pd = ProjectIO.load_project(example_path)
        self.assertEqual(pd.version, "1.0")
        self.assertEqual(len(pd.walls), 4)


if __name__ == "__main__":
    unittest.main()
