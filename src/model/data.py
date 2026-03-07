from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Optional
import math
import os
import uuid

from src.core.coordinate_system import CoordinateSystem

# Legacy type key → display-name key migration (BUG-004)
_LEGACY_TYPE_MAP = {
    # rooms
    "living_room": "Living Room",
    "kitchen": "Kitchen",
    "bedroom": "Bedroom",
    "bathroom": "Bathroom",
    "corridor": "Corridor",
    "balcony": "Balcony",
    "entrance": "Entrance",
    "utility": "Utility",
    # custom_polygons
    "clean_zone": "Clean Zone",
    "danger_zone": "Danger Zone",
    "complex_zone": "Complex Zone",
    # objects
    "furniture": "Furniture",
    "appliance": "Appliance",
    "obstacle": "Obstacle",
}


def _migrate_type(type_key: str) -> str:
    """Map legacy snake_case type keys to display-name keys."""
    return _LEGACY_TYPE_MAP.get(type_key, type_key)


def _degrees_to_quaternion(degrees: float, cs: CoordinateSystem) -> list:
    """Convert 2D rotation (degrees, CCW in floor plane) to quaternion [w,x,y,z].

    Rotation is about the up-axis of the coordinate system.
    """
    rad = math.radians(degrees)
    w = math.cos(rad / 2)
    axis = [0.0, 0.0, 0.0]
    axis[cs.up_axis] = math.sin(rad / 2) * cs.up_direction
    return [w, axis[0], axis[1], axis[2]]


def _quaternion_to_degrees(quat: list, cs: CoordinateSystem) -> float:
    """Convert quaternion [w,x,y,z] back to degrees (2D rotation about up-axis)."""
    w = quat[0]
    sin_comp = quat[1 + cs.up_axis]
    angle = 2 * math.atan2(sin_comp * cs.up_direction, w)
    return math.degrees(angle)

@dataclass
class Point2D:
    x: float
    y: float

    def to_tuple(self):
        return (self.x, self.y)

    @staticmethod
    def from_tuple(t):
        return Point2D(t[0], t[1])

@dataclass
class AnnotationBase:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = "default"
    z_min: float = 0.0
    z_max: float = 2.5

    def to_dict(self):
        return asdict(self)

@dataclass
class Wall(AnnotationBase):
    start: Point2D = field(default_factory=lambda: Point2D(0,0))
    end: Point2D = field(default_factory=lambda: Point2D(0,0))
    thickness: float = 0.1

    def to_dict(self):
        d = asdict(self)
        d['start'] = asdict(self.start)
        d['end'] = asdict(self.end)
        return d

    @staticmethod
    def from_dict(d):
        wall = Wall(
            id=d.get('id', str(uuid.uuid4())),
            category=d.get('category', 'default'),
            z_min=d.get('z_min', 0.0),
            z_max=d.get('z_max', 2.5),
            start=Point2D(**d['start']),
            end=Point2D(**d['end']),
            thickness=d.get('thickness', 0.1)
        )
        return wall

@dataclass
class Room(AnnotationBase):
    points: List[Point2D] = field(default_factory=list) # Polygon vertices
    name: str = "Room"
    room_type: str = "default"

    def to_dict(self):
        d = asdict(self)
        d['points'] = [asdict(p) for p in self.points]
        return d

    @staticmethod
    def from_dict(d):
        room = Room(
            id=d.get('id', str(uuid.uuid4())),
            category=d.get('category', 'default'),
            z_min=d.get('z_min', 0.0),
            z_max=d.get('z_max', 2.5),
            points=[Point2D(**p) for p in d['points']],
            name=d.get('name', 'Room'),
            room_type=d.get('room_type', 'default')
        )
        return room

@dataclass
class Object(AnnotationBase):
    center: Point2D = field(default_factory=lambda: Point2D(0, 0))
    width: float = 1.0
    height: float = 1.0
    rotation: float = 0.0  # Degrees
    object_type: str = "default"

    def to_dict(self):
        d = asdict(self)
        d['center'] = asdict(self.center)
        return d

    @staticmethod
    def from_dict(d):
        return Object(
            id=d.get('id', str(uuid.uuid4())),
            category=d.get('category', 'default'),
            z_min=d.get('z_min', 0.0),
            z_max=d.get('z_max', 2.5),
            center=Point2D(**d['center']),
            width=d.get('width', 1.0),
            height=d.get('height', 1.0),
            rotation=d.get('rotation', 0.0),
            object_type=d.get('object_type', 'default'),
        )

@dataclass
class CustomPolygon(AnnotationBase):
    points: List[Point2D] = field(default_factory=list)
    polygon_type: str = "default"  # e.g. "cleaning_zone", "complex_area"

    def to_dict(self):
        d = asdict(self)
        d['points'] = [asdict(p) for p in self.points]
        return d

    @staticmethod
    def from_dict(d):
        return CustomPolygon(
            id=d.get('id', str(uuid.uuid4())),
            category=d.get('category', 'default'),
            z_min=d.get('z_min', 0.0),
            z_max=d.get('z_max', 2.5),
            points=[Point2D(**p) for p in d.get('points', [])],
            polygon_type=d.get('polygon_type', 'default'),
        )

@dataclass
class MapMetadata:
    """ROS2 map_server compatible occupancy grid metadata."""
    image_path: str = ""
    image_path_absolute: str = ""
    resolution: float = 0.05
    origin_x: float = 0.0
    origin_y: float = 0.0
    origin_yaw: float = 0.0
    negate: int = 0
    occupied_thresh: float = 0.65
    free_thresh: float = 0.196
    image_width: int = 0
    image_height: int = 0

    def to_dict(self) -> dict:
        return {
            "image_path": self.image_path,
            "resolution": self.resolution,
            "origin_x": self.origin_x,
            "origin_y": self.origin_y,
            "origin_yaw": self.origin_yaw,
            "negate": self.negate,
            "occupied_thresh": self.occupied_thresh,
            "free_thresh": self.free_thresh,
            "image_width": self.image_width,
            "image_height": self.image_height,
        }

    @staticmethod
    def from_dict(d: dict) -> "MapMetadata":
        return MapMetadata(
            image_path=d.get("image_path", ""),
            image_path_absolute=d.get("image_path_absolute", ""),
            resolution=d.get("resolution", 0.05),
            origin_x=d.get("origin_x", 0.0),
            origin_y=d.get("origin_y", 0.0),
            origin_yaw=d.get("origin_yaw", 0.0),
            negate=d.get("negate", 0),
            occupied_thresh=d.get("occupied_thresh", 0.65),
            free_thresh=d.get("free_thresh", 0.196),
            image_width=d.get("image_width", 0),
            image_height=d.get("image_height", 0),
        )


@dataclass
class ProjectData:
    walls: List[Wall] = field(default_factory=list)
    rooms: List[Room] = field(default_factory=list)
    objects: List[Object] = field(default_factory=list)
    custom_polygons: List[CustomPolygon] = field(default_factory=list)
    coordinate_system: CoordinateSystem = field(default_factory=CoordinateSystem.ros)
    map_metadata: Optional[MapMetadata] = None
    version: str = "1.0"
    data_type: str = "point_cloud"
    created_at: Optional[str] = None
    modified_at: Optional[str] = None

    def to_dict(self):
        cs = self.coordinate_system
        fl = cs.floor_level

        # Walls → [[start_3d, end_3d], ...]
        walls_out = []
        for w in self.walls:
            walls_out.append([
                cs.make_3d_point(w.start.x, w.start.y, fl),
                cs.make_3d_point(w.end.x, w.end.y, fl),
            ])

        # Rooms → {id, type, points}
        rooms_out = []
        for r in self.rooms:
            rooms_out.append({
                "id": r.id,
                "type": r.room_type,
                "points": [cs.make_3d_point(p.x, p.y, fl) for p in r.points],
            })

        # Objects → {id, type, center, extent, rotation}
        objects_out = []
        for o in self.objects:
            center_z = (o.z_min + o.z_max) / 2.0
            depth = o.z_max - o.z_min
            objects_out.append({
                "id": o.id,
                "type": o.object_type,
                "center": cs.make_3d_point(o.center.x, o.center.y, center_z),
                "extent": [o.width, o.height, depth],
                "rotation": _degrees_to_quaternion(o.rotation, cs),
            })

        # Zones (from custom_polygons)
        zones_out = []
        for cp in self.custom_polygons:
            zones_out.append({
                "id": cp.id,
                "type": cp.polygon_type,
                "points": [cs.make_3d_point(p.x, p.y, fl) for p in cp.points],
            })

        d = {
            "version": "1.0",
            "data_type": self.data_type,
            "coordinate_system": cs.to_preset_name() or "ros",
            "layout": {"walls": walls_out, "rooms": rooms_out},
            "objects": objects_out,
            "zones": zones_out,
        }
        if cs.floor_level != 0.0:
            d["floor_level"] = cs.floor_level
        if self.created_at:
            d["created_at"] = self.created_at
        if self.modified_at:
            d["modified_at"] = self.modified_at
        if self.map_metadata is not None:
            d["source"] = self._build_source_dict()
        return d

    def _build_source_dict(self) -> dict:
        meta = self.map_metadata
        file_name = os.path.basename(meta.image_path) if meta.image_path else ""
        source: dict = {"file_name": file_name}
        if self.data_type == "occupancy_grid" and meta.resolution > 0:
            source["occupancy_grid"] = {
                "resolution": meta.resolution,
                "origin": [meta.origin_x, meta.origin_y, meta.origin_yaw],
                "negate": meta.negate,
                "occupied_thresh": meta.occupied_thresh,
                "free_thresh": meta.free_thresh,
            }
        return source

    @staticmethod
    def from_dict(d):
        return ProjectData._from_dict_v1(d)

    @staticmethod
    def _from_dict_v1(d):
        """Load v1.0 schema format (with 'layout' key)."""
        proj = ProjectData()
        proj.version = d.get("version", "1.0")
        proj.data_type = d.get("data_type", "point_cloud")
        proj.created_at = d.get("created_at")
        proj.modified_at = d.get("modified_at")

        # Coordinate system from string enum
        cs_name = d.get("coordinate_system", "ros")
        if isinstance(cs_name, str):
            proj.coordinate_system = CoordinateSystem.from_preset(cs_name)
        else:
            proj.coordinate_system = CoordinateSystem.from_dict(cs_name)
        proj.coordinate_system.floor_level = d.get("floor_level", 0.0)
        cs = proj.coordinate_system
        fh, fv = cs.floor_axes

        # Walls
        layout = d.get("layout", {})
        for wall_arr in layout.get("walls", []):
            start_3d, end_3d = wall_arr
            proj.walls.append(Wall(
                start=Point2D(start_3d[fh], start_3d[fv]),
                end=Point2D(end_3d[fh], end_3d[fv]),
            ))

        # Rooms
        for room_d in layout.get("rooms", []):
            pts = [Point2D(p[fh], p[fv]) for p in room_d["points"]]
            proj.rooms.append(Room(
                id=room_d["id"], points=pts, room_type=_migrate_type(room_d["type"]),
            ))

        # Objects
        for obj_d in d.get("objects", []):
            c3d = obj_d["center"]
            ext = obj_d["extent"]
            quat = obj_d["rotation"]
            rot_deg = _quaternion_to_degrees(quat, cs)
            depth = ext[2]
            center_h = c3d[cs.up_axis]
            proj.objects.append(Object(
                id=obj_d["id"],
                center=Point2D(c3d[fh], c3d[fv]),
                width=ext[0], height=ext[1],
                rotation=rot_deg,
                object_type=_migrate_type(obj_d["type"]),
                z_min=center_h - depth / 2,
                z_max=center_h + depth / 2,
            ))

        # Zones → CustomPolygon
        for zone_d in d.get("zones", []):
            pts = [Point2D(p[fh], p[fv]) for p in zone_d["points"]]
            proj.custom_polygons.append(CustomPolygon(
                id=zone_d["id"], points=pts, polygon_type=_migrate_type(zone_d["type"]),
            ))

        # Source → MapMetadata
        source = d.get("source")
        if source:
            meta = MapMetadata(image_path=source.get("file_name", ""))
            occ = source.get("occupancy_grid")
            if occ:
                meta.resolution = occ.get("resolution", 0.05)
                origin = occ.get("origin", [0, 0, 0])
                meta.origin_x = origin[0]
                meta.origin_y = origin[1]
                meta.origin_yaw = origin[2]
                meta.negate = occ.get("negate", 0)
                meta.occupied_thresh = occ.get("occupied_thresh", 0.65)
                meta.free_thresh = occ.get("free_thresh", 0.196)
            proj.map_metadata = meta

        return proj
