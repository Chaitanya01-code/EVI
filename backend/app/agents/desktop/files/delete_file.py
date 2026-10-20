from typing import Any, Dict

from app.agents.desktop.files.file_tools import delete_file as _delete_file


def delete_file(file_path: str, confirm: bool = False) -> Dict[str, Any]:
    return _delete_file(file_path)
