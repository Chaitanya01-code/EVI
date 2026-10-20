from typing import Any, Dict

from app.agents.desktop.files.file_tools import delete_folder as _delete_folder


def delete_folder(folder_path: str, confirm: bool = False) -> Dict[str, Any]:
    return _delete_folder(folder_path)
