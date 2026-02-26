import open3d.visualization.rendering as rendering


class AnnotationMixin:
    """Mixin providing annotation geometry sync methods for Viewer3D."""

    # --- Annotation Sync Methods ---

    def add_room_geometry(self, room_id: str, room_mesh):
        """
        Add room floor plane to scene.

        Args:
            room_id: Unique room identifier
            room_mesh: TriangleMesh of the room floor plane
        """
        if not self.renderer or self._renderer_failed:
            return

        # Always remove first to prevent duplicate-name silent failure in Open3D
        self.renderer.scene.remove_geometry(f"room_{room_id}")
        mat = rendering.MaterialRecord()
        mat.shader = "defaultLit"
        self.renderer.scene.add_geometry(f"room_{room_id}", room_mesh, mat)
        self.render_scene()

    def remove_room_geometry(self, room_id: str):
        """Remove room floor plane from scene."""
        if not self.renderer or self._renderer_failed:
            return

        self.renderer.scene.remove_geometry(f"room_{room_id}")
        self.render_scene()

    def add_wall_geometry(self, wall_id: str, wall_mesh):
        """
        Add virtual wall geometry to scene.

        Creates a 3D wall plane from 2D wall annotation.

        Args:
            wall_id: Unique identifier for the wall (e.g., "edge_12345")
            wall_mesh: Open3D TriangleMesh representing the wall
        """
        if not self.renderer or self._renderer_failed:
            return

        # Always remove first to prevent duplicate-name silent failure in Open3D
        self.renderer.scene.remove_geometry(f"wall_{wall_id}")
        mat = rendering.MaterialRecord()
        mat.shader = "defaultLit"
        self.renderer.scene.add_geometry(f"wall_{wall_id}", wall_mesh, mat)
        self.render_scene()

    def remove_wall_geometry(self, wall_id: str):
        """
        Remove virtual wall geometry from scene.

        Args:
            wall_id: Unique identifier for the wall to remove
        """
        if not self.renderer or self._renderer_failed:
            return

        # Remove from scene
        self.renderer.scene.remove_geometry(f"wall_{wall_id}")

        # Re-render
        self.render_scene()

    def clear_all_walls(self):
        """Remove all virtual wall geometries from scene."""
        # Note: This requires tracking wall IDs externally
        # Current implementation relies on annotation_sync to track and remove individually
        pass

    def add_custom_polygon_geometry(self, polygon_id: str, mesh):
        """Add custom polygon plane to scene."""
        if not self.renderer or self._renderer_failed:
            return
        self.renderer.scene.remove_geometry(f"cpoly_{polygon_id}")
        mat = rendering.MaterialRecord()
        mat.shader = "defaultLit"
        self.renderer.scene.add_geometry(f"cpoly_{polygon_id}", mesh, mat)
        self.render_scene()

    def remove_custom_polygon_geometry(self, polygon_id: str):
        """Remove custom polygon plane from scene."""
        if not self.renderer or self._renderer_failed:
            return
        self.renderer.scene.remove_geometry(f"cpoly_{polygon_id}")
        self.render_scene()

    def add_object_geometry(self, object_id: str, line_set):
        """Add object OBB wireframe to scene."""
        if not self.renderer or self._renderer_failed:
            return
        self.renderer.scene.remove_geometry(f"obj_{object_id}")
        mat = rendering.MaterialRecord()
        mat.shader = "unlitLine"
        mat.line_width = 2.0
        self.renderer.scene.add_geometry(f"obj_{object_id}", line_set, mat)
        self.render_scene()

    def remove_object_geometry(self, object_id: str):
        """Remove object OBB box from scene."""
        if not self.renderer or self._renderer_failed:
            return
        self.renderer.scene.remove_geometry(f"obj_{object_id}")
        self.render_scene()

    def set_geometry_visibility(self, visible: bool):
        """
        Toggle visibility of original geometry (point cloud/mesh).

        Args:
            visible: True to show, False to hide
        """
        if not self.renderer or self._renderer_failed:
            return

        self.geometry_visible = visible

        if visible:
            # Add geometry back to scene
            if self.geometry and self.material:
                self.renderer.scene.add_geometry("geometry", self.geometry, self.material)
        else:
            # Remove geometry from scene
            self.renderer.scene.remove_geometry("geometry")

        self.render_scene()
