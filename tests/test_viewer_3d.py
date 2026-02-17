"""
Tests for Viewer3D renderer creation, cleanup, resize handling, and graceful degradation.

Covers:
- _create_renderer with valid dimensions
- _create_renderer cleanup of old renderer before creating new one
- _create_renderer failure handling (sets _renderer_failed, renderer=None)
- showEvent schedules delayed renderer creation
- resizeEvent recreates renderer safely
- resizeEvent skips when _renderer_failed is True
- resizeEvent skips when widget not yet shown
- resizeEvent skips invalid dimensions (0 or negative)
- paintEvent shows error message when renderer failed
- paintEvent shows image when available
- paintEvent shows loading message when no image
- render_scene with no renderer is a no-op
- load_geometry skips when renderer failed
- update_slice_plane skips when renderer failed
"""
import unittest
from unittest.mock import MagicMock, patch, PropertyMock, call
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSize, Qt, QPoint
from PyQt6.QtGui import QImage, QPainter, QColor
import numpy as np
import sys

# Ensure QApplication exists
if not QApplication.instance():
    app = QApplication(sys.argv)


class TestViewer3DRendererCreation(unittest.TestCase):
    """Tests for _create_renderer method."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        """Create a Viewer3D with mocked Open3D to avoid GPU dependency."""
        self.mock_rendering = mock_rendering
        self.mock_o3d = mock_o3d

        # Mock MaterialRecord
        mock_material = MagicMock()
        mock_rendering.MaterialRecord.return_value = mock_material

        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_with_valid_dimensions(self, mock_rendering):
        """_create_renderer creates an OffscreenRenderer with the given w, h."""
        mock_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = mock_renderer

        self.viewer._create_renderer(800, 600)

        mock_rendering.OffscreenRenderer.assert_called_once_with(800, 600)
        self.assertIs(self.viewer.renderer, mock_renderer)
        self.assertFalse(self.viewer._renderer_failed)

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_sets_background(self, mock_rendering):
        """_create_renderer sets the scene background color."""
        mock_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = mock_renderer

        self.viewer._create_renderer(800, 600)

        mock_renderer.scene.set_background.assert_called_once_with([0.9, 0.9, 0.9, 1.0])

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_enables_sun_light(self, mock_rendering):
        """_create_renderer configures sun light on the scene."""
        mock_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = mock_renderer

        self.viewer._create_renderer(800, 600)

        mock_renderer.scene.scene.set_sun_light.assert_called_once()
        mock_renderer.scene.scene.enable_sun_light.assert_called_once_with(True)

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_cleans_up_old_renderer(self, mock_rendering):
        """_create_renderer clears geometry and deletes old renderer first."""
        old_renderer = MagicMock()
        self.viewer.renderer = old_renderer

        new_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = new_renderer

        self.viewer._create_renderer(800, 600)

        # Old renderer scene geometry should have been cleared
        old_renderer.scene.clear_geometry.assert_called_once()
        # New renderer should be set
        self.assertIs(self.viewer.renderer, new_renderer)

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_cleanup_tolerates_clear_geometry_failure(self, mock_rendering):
        """_create_renderer handles failure in old renderer cleanup gracefully."""
        old_renderer = MagicMock()
        old_renderer.scene.clear_geometry.side_effect = RuntimeError("GPU error")
        self.viewer.renderer = old_renderer

        new_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = new_renderer

        # Should not raise
        self.viewer._create_renderer(800, 600)

        # New renderer still created
        self.assertIs(self.viewer.renderer, new_renderer)

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_readds_geometry_if_present(self, mock_rendering):
        """_create_renderer re-adds existing geometry and material after recreation."""
        mock_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = mock_renderer

        self.viewer.geometry = MagicMock()
        self.viewer.material = MagicMock()

        self.viewer._create_renderer(800, 600)

        mock_renderer.scene.add_geometry.assert_any_call(
            "geometry", self.viewer.geometry, self.viewer.material
        )

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_readds_plane_if_present(self, mock_rendering):
        """_create_renderer re-adds plane geometry after recreation."""
        mock_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = mock_renderer

        self.viewer.plane_geometry = MagicMock()

        self.viewer._create_renderer(800, 600)

        # Check that "plane" was added (second call to add_geometry)
        add_calls = mock_renderer.scene.add_geometry.call_args_list
        plane_calls = [c for c in add_calls if c[0][0] == "plane"]
        self.assertEqual(len(plane_calls), 1)

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_does_not_readd_geometry_when_none(self, mock_rendering):
        """_create_renderer skips geometry re-add when geometry is None."""
        mock_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = mock_renderer

        self.viewer.geometry = None
        self.viewer.plane_geometry = None

        self.viewer._create_renderer(800, 600)

        mock_renderer.scene.add_geometry.assert_not_called()

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_failure_sets_renderer_failed(self, mock_rendering):
        """_create_renderer sets _renderer_failed on exception."""
        mock_rendering.OffscreenRenderer.side_effect = RuntimeError("No OpenGL")

        self.viewer._create_renderer(800, 600)

        self.assertTrue(self.viewer._renderer_failed)
        self.assertIsNone(self.viewer.renderer)

    @patch('src.gui.viewer_3d.rendering')
    def test_create_renderer_calls_render_scene(self, mock_rendering):
        """_create_renderer calls render_scene after successful creation."""
        mock_renderer = MagicMock()
        mock_rendering.OffscreenRenderer.return_value = mock_renderer

        with patch.object(self.viewer, 'render_scene') as mock_render:
            self.viewer._create_renderer(800, 600)
            mock_render.assert_called_once()


class TestViewer3DResizeEvent(unittest.TestCase):
    """Tests for resizeEvent handling."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()

    def _make_resize_event(self, w, h):
        """Create a mock QResizeEvent with given size."""
        event = MagicMock()
        event.size.return_value = QSize(w, h)
        return event

    def test_resize_skips_when_renderer_failed(self):
        """resizeEvent returns early if _renderer_failed is True."""
        self.viewer._renderer_failed = True
        self.viewer._shown_once = True

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch('PyQt6.QtWidgets.QWidget.resizeEvent'):
                event = self._make_resize_event(800, 600)
                self.viewer.resizeEvent(event)
                mock_create.assert_not_called()

    def test_resize_skips_when_not_shown(self):
        """resizeEvent returns early if widget has not been shown yet."""
        self.viewer._renderer_failed = False
        self.viewer._shown_once = False

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch('PyQt6.QtWidgets.QWidget.resizeEvent'):
                event = self._make_resize_event(800, 600)
                self.viewer.resizeEvent(event)
                mock_create.assert_not_called()

    def test_resize_skips_zero_width(self):
        """resizeEvent returns early for zero width."""
        self.viewer._renderer_failed = False
        self.viewer._shown_once = True

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch('PyQt6.QtWidgets.QWidget.resizeEvent'):
                event = self._make_resize_event(0, 600)
                self.viewer.resizeEvent(event)
                mock_create.assert_not_called()

    def test_resize_skips_zero_height(self):
        """resizeEvent returns early for zero height."""
        self.viewer._renderer_failed = False
        self.viewer._shown_once = True

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch('PyQt6.QtWidgets.QWidget.resizeEvent'):
                event = self._make_resize_event(800, 0)
                self.viewer.resizeEvent(event)
                mock_create.assert_not_called()

    def test_resize_skips_negative_dimensions(self):
        """resizeEvent returns early for negative dimensions."""
        self.viewer._renderer_failed = False
        self.viewer._shown_once = True

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch('PyQt6.QtWidgets.QWidget.resizeEvent'):
                event = self._make_resize_event(-1, -1)
                self.viewer.resizeEvent(event)
                mock_create.assert_not_called()

    def test_resize_creates_renderer_when_valid(self):
        """resizeEvent calls _create_renderer with valid dimensions after widget shown."""
        self.viewer._renderer_failed = False
        self.viewer._shown_once = True

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch('PyQt6.QtWidgets.QWidget.resizeEvent'):
                event = self._make_resize_event(800, 600)
                self.viewer.resizeEvent(event)
                mock_create.assert_called_once_with(800, 600)

    def test_resize_creates_renderer_with_new_dimensions(self):
        """resizeEvent passes the event's dimensions to _create_renderer."""
        self.viewer._renderer_failed = False
        self.viewer._shown_once = True

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch('PyQt6.QtWidgets.QWidget.resizeEvent'):
                event = self._make_resize_event(1920, 1080)
                self.viewer.resizeEvent(event)
                mock_create.assert_called_once_with(1920, 1080)


class TestViewer3DShowEvent(unittest.TestCase):
    """Tests for showEvent handling."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()

    def test_show_event_sets_shown_once(self):
        """showEvent sets _shown_once to True."""
        self.assertFalse(self.viewer._shown_once)

        with patch('PyQt6.QtCore.QTimer') as mock_timer:
            with patch('PyQt6.QtWidgets.QWidget.showEvent'):
                event = MagicMock()
                self.viewer.showEvent(event)

        self.assertTrue(self.viewer._shown_once)

    def test_show_event_schedules_timer(self):
        """showEvent schedules a QTimer.singleShot with 200ms delay."""
        with patch('PyQt6.QtCore.QTimer') as mock_timer:
            with patch('PyQt6.QtWidgets.QWidget.showEvent'):
                event = MagicMock()
                self.viewer.showEvent(event)

                mock_timer.singleShot.assert_called_once()
                args = mock_timer.singleShot.call_args[0]
                self.assertEqual(args[0], 200)  # 200ms delay


class TestViewer3DShowEventDelayedCallback(unittest.TestCase):
    """Tests for the delayed callback scheduled by showEvent."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()

    def test_delayed_callback_creates_renderer_when_not_failed(self):
        """The delayed callback creates renderer if not already created and not failed."""
        self.viewer.renderer = None
        self.viewer._renderer_failed = False

        # Capture the callback
        with patch('PyQt6.QtCore.QTimer') as mock_timer:
            with patch('PyQt6.QtWidgets.QWidget.showEvent'):
                # Make widget think it has valid size
                self.viewer.resize(800, 600)

                event = MagicMock()
                self.viewer.showEvent(event)

                callback = mock_timer.singleShot.call_args[0][1]

        # Invoke the callback
        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch.object(self.viewer, 'width', return_value=800):
                with patch.object(self.viewer, 'height', return_value=600):
                    callback()
                    mock_create.assert_called_once_with(800, 600)

    def test_delayed_callback_skips_if_renderer_exists(self):
        """The delayed callback does nothing if renderer already exists."""
        self.viewer.renderer = MagicMock()  # Already has renderer

        with patch('PyQt6.QtCore.QTimer') as mock_timer:
            with patch('PyQt6.QtWidgets.QWidget.showEvent'):
                event = MagicMock()
                self.viewer.showEvent(event)
                callback = mock_timer.singleShot.call_args[0][1]

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            callback()
            mock_create.assert_not_called()

    def test_delayed_callback_skips_if_renderer_failed(self):
        """The delayed callback does nothing if renderer previously failed."""
        self.viewer.renderer = None
        self.viewer._renderer_failed = True

        with patch('PyQt6.QtCore.QTimer') as mock_timer:
            with patch('PyQt6.QtWidgets.QWidget.showEvent'):
                event = MagicMock()
                self.viewer.showEvent(event)
                callback = mock_timer.singleShot.call_args[0][1]

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            callback()
            mock_create.assert_not_called()

    def test_delayed_callback_skips_zero_size(self):
        """The delayed callback does nothing if widget has zero dimensions."""
        self.viewer.renderer = None
        self.viewer._renderer_failed = False

        with patch('PyQt6.QtCore.QTimer') as mock_timer:
            with patch('PyQt6.QtWidgets.QWidget.showEvent'):
                event = MagicMock()
                self.viewer.showEvent(event)
                callback = mock_timer.singleShot.call_args[0][1]

        with patch.object(self.viewer, '_create_renderer') as mock_create:
            with patch.object(self.viewer, 'width', return_value=0):
                with patch.object(self.viewer, 'height', return_value=0):
                    callback()
                    mock_create.assert_not_called()


class TestViewer3DPaintEvent(unittest.TestCase):
    """Tests for paintEvent behavior."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()
        self.viewer.resize(200, 200)

    @patch('src.gui.viewer_3d.QPainter')
    def test_paint_shows_error_when_renderer_failed(self, mock_painter_cls):
        """paintEvent shows error message when _renderer_failed is True."""
        self.viewer._renderer_failed = True
        mock_painter = MagicMock()
        mock_painter_cls.return_value = mock_painter

        event = MagicMock()
        self.viewer.paintEvent(event)

        # Verify drawText was called with error message content
        draw_text_calls = [
            c for c in mock_painter.drawText.call_args_list
        ]
        self.assertTrue(len(draw_text_calls) > 0)
        # Check that the error message contains key text
        text_arg = draw_text_calls[0][0][-1]  # Last positional arg is the text
        self.assertIn("Viewer3D Disabled", text_arg)

    @patch('src.gui.viewer_3d.QPainter')
    def test_paint_shows_no_data_when_no_image(self, mock_painter_cls):
        """paintEvent shows 'No Data / Loading...' when no image is available."""
        self.viewer._renderer_failed = False
        self.viewer.image = None
        mock_painter = MagicMock()
        mock_painter_cls.return_value = mock_painter

        event = MagicMock()
        self.viewer.paintEvent(event)

        draw_text_calls = mock_painter.drawText.call_args_list
        self.assertTrue(len(draw_text_calls) > 0)
        text_arg = draw_text_calls[0][0][-1]
        self.assertIn("No Data", text_arg)

    @patch('src.gui.viewer_3d.QPainter')
    def test_paint_draws_image_when_available(self, mock_painter_cls):
        """paintEvent draws the image when renderer succeeded and image exists."""
        self.viewer._renderer_failed = False
        self.viewer.image = MagicMock()
        mock_painter = MagicMock()
        mock_painter_cls.return_value = mock_painter

        event = MagicMock()
        self.viewer.paintEvent(event)

        mock_painter.drawImage.assert_called_once_with(0, 0, self.viewer.image)


class TestViewer3DRenderScene(unittest.TestCase):
    """Tests for render_scene method."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()

    def test_render_scene_noop_when_no_renderer(self):
        """render_scene returns immediately if renderer is None."""
        self.viewer.renderer = None
        # Should not raise
        self.viewer.render_scene()
        # No image should be set
        self.assertIsNone(self.viewer.image)


class TestViewer3DGracefulDegradation(unittest.TestCase):
    """Tests for graceful degradation when renderer fails."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()

    def test_load_geometry_skips_when_failed(self):
        """load_geometry returns early when _renderer_failed is True."""
        self.viewer._renderer_failed = True
        # Should not raise, should be a no-op
        self.viewer.load_geometry("/nonexistent/file.ply")

    def test_update_slice_plane_skips_when_failed(self):
        """update_slice_plane returns early when _renderer_failed is True."""
        self.viewer._renderer_failed = True
        # Should not raise
        self.viewer.update_slice_plane(1.0)

    def test_material_creation_failure_sets_renderer_failed(self):
        """If MaterialRecord fails, _renderer_failed is set to True."""
        with patch('src.gui.viewer_3d.rendering') as mock_rendering:
            mock_rendering.MaterialRecord.side_effect = RuntimeError("No GPU")
            with patch('src.gui.viewer_3d.o3d'):
                from src.gui.viewer_3d import Viewer3D
                viewer = Viewer3D()
                self.assertTrue(viewer._renderer_failed)
                self.assertIsNone(viewer.material)


class TestViewer3DInitialization(unittest.TestCase):
    """Tests for Viewer3D __init__ defaults."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def test_initial_state(self, mock_o3d, mock_rendering):
        """Viewer3D initializes with correct default state."""
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        viewer = Viewer3D()

        self.assertIsNone(viewer.renderer)
        self.assertIsNone(viewer.image)
        self.assertIsNone(viewer._image_data)
        self.assertFalse(viewer._renderer_failed)
        self.assertFalse(viewer._shown_once)
        self.assertIsNone(viewer.geometry)
        self.assertIsNone(viewer.plane_geometry)

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def test_initial_camera_state(self, mock_o3d, mock_rendering):
        """Viewer3D initializes with correct camera defaults."""
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        viewer = Viewer3D()

        np.testing.assert_array_equal(viewer.camera_eye, [0.0, 0.0, 10.0])
        np.testing.assert_array_equal(viewer.camera_center, [0.0, 0.0, 0.0])
        np.testing.assert_array_equal(viewer.camera_up, [0.0, 1.0, 0.0])
        self.assertEqual(viewer.fov, 60.0)

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def test_initial_interaction_state(self, mock_o3d, mock_rendering):
        """Viewer3D initializes with no active interaction."""
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        viewer = Viewer3D()

        self.assertFalse(viewer.is_rotating)
        self.assertFalse(viewer.is_panning)


class TestViewer3DMouseInteraction(unittest.TestCase):
    """Tests for mouse interaction state management."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()

    def test_left_click_starts_rotation(self):
        """Left mouse press enables rotation mode."""
        event = MagicMock()
        event.button.return_value = Qt.MouseButton.LeftButton
        event.pos.return_value = QPoint(100, 100)

        self.viewer.mousePressEvent(event)
        self.assertTrue(self.viewer.is_rotating)
        self.assertFalse(self.viewer.is_panning)

    def test_middle_click_starts_panning(self):
        """Middle mouse press enables panning mode."""
        event = MagicMock()
        event.button.return_value = Qt.MouseButton.MiddleButton
        event.pos.return_value = QPoint(100, 100)

        self.viewer.mousePressEvent(event)
        self.assertFalse(self.viewer.is_rotating)
        self.assertTrue(self.viewer.is_panning)

    def test_mouse_release_resets_interaction(self):
        """Mouse release disables both rotation and panning."""
        self.viewer.is_rotating = True
        self.viewer.is_panning = True

        event = MagicMock()
        self.viewer.mouseReleaseEvent(event)

        self.assertFalse(self.viewer.is_rotating)
        self.assertFalse(self.viewer.is_panning)


class TestViewer3DRotationMatrix(unittest.TestCase):
    """Tests for the rotation_matrix utility method."""

    @patch('src.gui.viewer_3d.rendering')
    @patch('src.gui.viewer_3d.o3d')
    def setUp(self, mock_o3d, mock_rendering):
        mock_rendering.MaterialRecord.return_value = MagicMock()
        from src.gui.viewer_3d import Viewer3D
        self.viewer = Viewer3D()

    def test_identity_rotation(self):
        """Rotation by 0 radians produces identity matrix."""
        R = self.viewer.rotation_matrix(np.array([0, 0, 1]), 0.0)
        np.testing.assert_array_almost_equal(R, np.eye(3))

    def test_90_degree_rotation_around_z(self):
        """90-degree rotation around Z axis rotates X to Y."""
        import math
        R = self.viewer.rotation_matrix(np.array([0, 0, 1]), math.pi / 2)
        # Rotating (1,0,0) by 90 degrees around Z should give (0,1,0)
        v = np.array([1, 0, 0])
        result = R @ v
        np.testing.assert_array_almost_equal(result, [0, 1, 0])

    def test_180_degree_rotation_around_y(self):
        """180-degree rotation around Y axis flips X."""
        import math
        R = self.viewer.rotation_matrix(np.array([0, 1, 0]), math.pi)
        v = np.array([1, 0, 0])
        result = R @ v
        np.testing.assert_array_almost_equal(result, [-1, 0, 0], decimal=10)


if __name__ == "__main__":
    unittest.main()
