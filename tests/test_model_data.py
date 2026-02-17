import unittest
from dataclasses import asdict
from src.model.data import Point2D, Wall, Room, ProjectData

class TestDataModel(unittest.TestCase):
    def test_point2d(self):
        p = Point2D(1.0, 2.0)
        d = asdict(p)
        self.assertEqual(d, {"x": 1.0, "y": 2.0})
        # Test from_dict ? Point2D doesn't have from_dict, just from_tuple or constructor
        # Wall uses Point2D(**d['start']) so constructor works.
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

if __name__ == "__main__":
    unittest.main()
