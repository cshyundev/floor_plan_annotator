import json
from pathlib import Path

import jsonschema

from src.model.data import ProjectData

_SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "annotations.v4.schema.json"


class ProjectIO:
    @staticmethod
    def save_project(project_data: ProjectData, filepath: str):
        data = project_data.to_dict()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load_project(filepath: str) -> ProjectData:
        with open(filepath, 'r') as f:
            data = json.load(f)
        schema = json.loads(_SCHEMA_PATH.read_text())
        jsonschema.validate(instance=data, schema=schema)
        return ProjectData.from_dict(data)
