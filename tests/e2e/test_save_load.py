"""E2E tests for save/load project roundtrip."""
import os
import tempfile

import numpy as np
import pytest

from src.gui.items import EdgeItem, RoomItem, ObjectItem, CustomPolygonItem
from src.core.io import ProjectIO
from tests.conftest import (
    draw_wall, draw_room, draw_object, draw_custom_polygon, items_of_type,
)


def _reload_from_data(canvas, data):
    """Load data into canvas, then restore the dummy background.

    scene.clear() inside load_from_data destroys the C++ background pixmap,
    so we must clear the stale reference first and re-apply the background
    after loading (matching real app flow: load project -> update background).
    """
    canvas.background_item = None
    canvas.load_from_data(data)
    img = np.zeros((500, 500), dtype=np.uint8)
    canvas.update_background(img, (0.0, 0.0, 10.0, 10.0), 50.0)


@pytest.mark.e2e
class TestSaveLoadRoundtrip:

    def test_wall_roundtrip(self, canvas, undo_stack):
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)

        data = canvas.save_to_data()
        assert len(data.walls) == 1
        assert abs(data.walls[0].start.x - 1.0) < 0.1
        assert abs(data.walls[0].end.x - 5.0) < 0.1

        _reload_from_data(canvas, data)
        assert len(items_of_type(canvas, EdgeItem)) == 1

    def test_room_roundtrip(self, canvas, undo_stack):
        draw_room(canvas, [(1, 1), (5, 1), (3, 4)], room_type="bedroom")

        data = canvas.save_to_data()
        assert len(data.rooms) == 1
        assert data.rooms[0].room_type == "bedroom"

        _reload_from_data(canvas, data)
        rooms = items_of_type(canvas, RoomItem)
        assert len(rooms) == 1
        assert rooms[0].room_type == "bedroom"

    def test_object_roundtrip(self, canvas, undo_stack):
        draw_object(canvas, 2.0, 2.0, 6.0, 4.0, object_type="appliance")

        data = canvas.save_to_data()
        assert len(data.objects) == 1

        _reload_from_data(canvas, data)
        objects = items_of_type(canvas, ObjectItem)
        assert len(objects) == 1
        assert objects[0].object_type == "appliance"

    def test_custom_polygon_roundtrip(self, canvas, undo_stack):
        draw_custom_polygon(canvas, [(1, 1), (4, 1), (4, 3), (1, 3)])

        data = canvas.save_to_data()
        assert len(data.custom_polygons) == 1

        _reload_from_data(canvas, data)
        polygons = items_of_type(canvas, CustomPolygonItem)
        assert len(polygons) == 1

    def test_full_project_json_roundtrip(self, canvas, undo_stack):
        """Save full scene to JSON file, load back, verify."""
        draw_wall(canvas, 1.0, 1.0, 5.0, 1.0)
        draw_room(canvas, [(1, 2), (4, 2), (2.5, 4)], room_type="kitchen")
        draw_object(canvas, 6.0, 6.0, 8.0, 7.0, object_type="furniture")

        data = canvas.save_to_data()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            ProjectIO.save_project(data, tmp_path)
            loaded = ProjectIO.load_project(tmp_path)

            assert len(loaded.walls) == len(data.walls)
            assert len(loaded.rooms) == len(data.rooms)
            assert len(loaded.objects) == len(data.objects)

            _reload_from_data(canvas, loaded)
            assert len(items_of_type(canvas, EdgeItem)) >= 1
            assert len(items_of_type(canvas, RoomItem)) == 1
            assert len(items_of_type(canvas, ObjectItem)) == 1
        finally:
            os.unlink(tmp_path)

    def test_load_clears_previous_scene(self, canvas, undo_stack):
        """Loading data replaces existing scene content."""
        draw_room(canvas, [(1, 1), (3, 1), (2, 3)])
        draw_room(canvas, [(5, 1), (7, 1), (6, 3)])
        assert len(items_of_type(canvas, RoomItem)) == 2

        # Save with 2 rooms, then add a 3rd
        data = canvas.save_to_data()
        draw_room(canvas, [(1, 5), (3, 5), (2, 7)])
        assert len(items_of_type(canvas, RoomItem)) == 3

        # Load should restore to 2 rooms
        _reload_from_data(canvas, data)
        assert len(items_of_type(canvas, RoomItem)) == 2
