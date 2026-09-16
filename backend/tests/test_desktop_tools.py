import unittest
from unittest.mock import patch

from app.agents.desktop.applications import Application, find_app
from app.agents.desktop.tools import open_app


class DesktopToolTests(unittest.TestCase):
    def test_find_app_normalizes_names_and_uses_discovered_apps(self):
        discovered = [Application("Visual Studio Code", "code.cmd", "Code.exe")]
        with patch("app.agents.desktop.applications.list_apps", return_value=discovered):
            self.assertEqual(find_app("visual studio code editor"), discovered[0])

    def test_open_app_returns_clean_not_found_result(self):
        with patch("app.agents.desktop.tools.find_app", return_value=None):
            result = open_app("Unknown Application")
        self.assertEqual(result, {
            "success": False,
            "verified": False,
            "message": "I couldn't find Unknown Application.",
        })

    def test_open_app_uses_discovered_command(self):
        application = Application("Notepad", "notepad.exe")
        with patch("app.agents.desktop.tools.find_app", return_value=application), \
                patch("app.agents.desktop.tools.subprocess.Popen") as popen:
            result = open_app("notepad")
        popen.assert_called_once()
        self.assertTrue(result["success"])


if __name__ == "__main__":
    unittest.main()