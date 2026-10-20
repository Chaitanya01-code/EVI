from typing import Any, Dict

from app.agents.desktop.files.file_tools import create_folder as _create_folder


def create_folder(folder_name: str, location: str = "") -> Dict[str, Any]:
    return _create_folder(folder_name, location)
