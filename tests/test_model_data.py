import unittest
from dataclasses import asdict
from src.model.data import Point2D, Wall, Room, Object, CustomPolygon, ProjectData

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

if __name__ == "__main__":
    unittest.main()
