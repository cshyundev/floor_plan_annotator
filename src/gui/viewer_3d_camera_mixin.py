import math
import numpy as np


class CameraMixin:
    """Mixin providing camera orbit/pan/zoom/rotation methods for Viewer3D."""

    def orbit_camera(self, dx, dy):
        # Simple Orbit around camera_center
        # Azimuth (dx) and Elevation (dy)

        # Vector from center to eye
        v = self.camera_eye - self.camera_center

        sensitivity = 0.01
        alpha = -dx * sensitivity
        beta = -dy * sensitivity

        # Right vector
        forward = (self.camera_center - self.camera_eye)
        fwd_norm = np.linalg.norm(forward)
        if fwd_norm < 1e-6:
            return
        forward = forward / fwd_norm
        right = np.cross(forward, self.camera_up)
        right_norm = np.linalg.norm(right)
        if right_norm < 1e-6:
            return  # Degenerate: forward parallel to camera_up
        right = right / right_norm

        # Rotate v around the up axis
        R_y = self.rotation_matrix(self.camera_up, alpha)
        v = R_y @ v

        # Rotate v around Right
        R_x = self.rotation_matrix(right, beta)
        v = R_x @ v

        # Update Eye
        self.camera_eye = self.camera_center + v

        self.render_scene()

    def pan_camera(self, dx, dy):
        sensitivity = 0.01

        forward = (self.camera_center - self.camera_eye)
        dist = np.linalg.norm(forward)
        if dist < 1e-6:
            return
        forward = forward / dist

        right = np.cross(forward, self.camera_up)
        right_norm = np.linalg.norm(right)
        if right_norm < 1e-6:
            return
        right = right / right_norm

        up = np.cross(right, forward)

        # Scale movement by distance
        move = -right * dx * sensitivity * (dist/10.0) + up * dy * sensitivity * (dist/10.0)

        self.camera_eye += move
        self.camera_center += move

        self.render_scene()

    def zoom_camera(self, delta):
        # Move eye towards center
        v = self.camera_center - self.camera_eye
        dist = np.linalg.norm(v)
        if dist < 1e-6:
            return

        zoom_speed = 0.1 * (dist if dist > 0.1 else 0.1)

        if delta > 0:
            step = 1.0 * zoom_speed
        else:
            step = -1.0 * zoom_speed

        move = (v / dist) * step

        # Don't pass center
        if np.linalg.norm(move) < dist:
            self.camera_eye += move

        self.render_scene()

    def rotation_matrix(self, axis, theta):
        """
        Return the rotation matrix associated with counterclockwise rotation about
        the given axis by theta radians.
        """
        axis = np.asarray(axis)
        axis = axis / math.sqrt(np.dot(axis, axis))
        a = math.cos(theta / 2.0)
        b, c, d = -axis * math.sin(theta / 2.0)
        aa, bb, cc, dd = a * a, b * b, c * c, d * d
        bc, ad, ac, ab, bd, cd = b * c, a * d, a * c, a * b, b * d, c * d
        return np.array([[aa + bb - cc - dd, 2 * (bc + ad), 2 * (bd - ac)],
                         [2 * (bc - ad), aa + cc - bb - dd, 2 * (cd + ab)],
                         [2 * (bd + ac), 2 * (cd - ab), aa + dd - bb - cc]])
