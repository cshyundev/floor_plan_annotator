import json

from src.model.data import ProjectData


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
        return ProjectData.from_dict(data)
