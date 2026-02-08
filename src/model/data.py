from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Optional
import uuid

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
    center: Point2D = field(default_factory=lambda: Point2D(0,0))
    width: float = 1.0
    height: float = 1.0
    rotation: float = 0.0 # Degrees
    
@dataclass
class ProjectData:
    walls: List[Wall] = field(default_factory=list)
    rooms: List[Room] = field(default_factory=list)
    objects: List[Object] = field(default_factory=list)
    version: str = "1.0"
    
    def to_dict(self):
        return {
            "version": self.version,
            "walls": [w.to_dict() for w in self.walls],
            "rooms": [r.to_dict() for r in self.rooms],
            "objects": [] # Not implemented yet
        }
        
    @staticmethod
    def from_dict(d):
        proj = ProjectData()
        proj.version = d.get('version', "1.0")
        proj.walls = [Wall.from_dict(w) for w in d.get('walls', [])]
        proj.rooms = [Room.from_dict(r) for r in d.get('rooms', [])]
        return proj
