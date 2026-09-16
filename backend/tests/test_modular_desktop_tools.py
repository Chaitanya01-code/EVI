import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.agents.desktop.applications import (
    Application,
    close_app,
    find_app,
    list_apps,
    open_app,
    restart_app,
)
from app.agents.desktop.files import (
    copy_file,
    delete_file,
    move_file,
    open_file,
    rename_file,
    search_file,
)
from app.agents.desktop.folders import (
    create_folder,
    delete_folder,
    move_folder,
    open_folder,
    rename_folder,
)
from app.agents.desktop.input import (
    mouse_click,
    mouse_move,
    press_key,
    type_text,
)
from app.agents.desktop.registry import desktop_tools
from app.agents.desktop.screen import (
    find_ui_element,
    inspect_screen,
    screenshot,
)
from app.agents.desktop.system import (
    lock,
    restart,
    shutdown,
    sleep,
)
from app.agents.desktop.terminal import (
    classify_command,
    get_output,
    run_command,
    run_script,
)
from app.agents.desktop.windows import (
    maximize_window,
    minimize_window,
    move_window,
    resize_window,
    switch_window,
)


class ModularDesktopToolsTests(unittest.TestCase):
    def test_registry_indexes_all_tools_and_aliases(self):
        expected_tools = (
            "applications.open_app",
            "applications.close_app",
            "applications.restart_app",
            "applications.list_apps",
            "applications.find_app",
            "windows.switch_window",
            "windows.minimize_window",
            "windows.maximize_window",
            "windows.resize_window",
            "windows.move_window",
            "files.open_file",
            "files.copy_file",
            "files.move_file",
            "files.rename_file",
            "files.delete_file",
            "files.search_file",
            "folders.create_folder",
            "folders.open_folder",
            "folders.rename_folder",
            "folders.move_folder",
            "folders.delete_folder",
            "system.shutdown",
            "system.restart",
            "system.lock",
            "system.sleep",
            "input.mouse_click",
            "input.mouse_move",
            "input.type_text",
            "input.press_key",
            "screen.screenshot",
            "screen.inspect_screen",
            "screen.find_ui_element",
            "terminal.run_command",
            "terminal.run_script",
            "terminal.get_output",
        )
        for tool_name in expected_tools:
            self.assertIsNotNone(desktop_tools.resolve(tool_name), f"Tool {tool_name} was not resolved")

        # Check aliases
        self.assertEqual(desktop_tools.resolve("open_app"), desktop_tools.resolve("applications.open_app"))
        self.assertEqual(desktop_tools.resolve("open_application"), desktop_tools.resolve("applications.open_app"))
        self.assertEqual(desktop_tools.resolve("switch_window"), desktop_tools.resolve("windows.switch_window"))
        self.assertEqual(desktop_tools.resolve("create_folder"), desktop_tools.resolve("folders.create_folder"))

    def test_application_discovery_without_hardcoding(self):
        fake_apps = [
            Application("Google Chrome", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "chrome.exe"),
            Application("Visual Studio Code", "C:\\Users\\user\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe", "Code.exe"),
            Application("Discord", "C:\\Users\\user\\AppData\\Local\\Discord\\app.ico", "Discord.exe"),
        ]
        with patch("app.agents.desktop.applications.list_apps", return_value=fake_apps):
            self.assertEqual(find_app("Chrome"), fake_apps[0])
            self.assertEqual(find_app("google chrome"), fake_apps[0])
            self.assertEqual(find_app("vs code"), fake_apps[1])
            self.assertEqual(find_app("visual studio code"), fake_apps[1])
            self.assertEqual(find_app("discord"), fake_apps[2])
            self.assertIsNone(find_app("NonExistentAppXYZ123"))

    def test_open_app_runs_process(self):
        app = Application("Calculator", "calc.exe", "calc.exe")
        with patch("app.agents.desktop.applications.open_app.find_app", return_value=app), \
                patch("subprocess.Popen") as popen:
            res = open_app("Calculator")
            self.assertTrue(res["success"])
            self.assertEqual(res["target"], "Calculator")
            popen.assert_called_once()

    def test_close_app_uses_taskkill(self):
        app = Application("Chrome", "chrome.exe", "chrome.exe")
        with patch("app.agents.desktop.applications.close_app.find_app", return_value=app), \
                patch("subprocess.run") as run:
            run.return_value.returncode = 0
            res = close_app("Chrome")
            self.assertTrue(res["success"])
            self.assertIn("closed", res["message"])

    def test_file_and_folder_operations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            # Create folder
            created = create_folder("TestEVI", location=str(temp_path))
            self.assertTrue(created["success"])
            folder_path = temp_path / "TestEVI"
            self.assertTrue(folder_path.exists())

            # Create test file
            src_file = folder_path / "test.txt"
            src_file.write_text("hello evi")

            # Rename file
            renamed = rename_file(str(src_file), "final.txt")
            self.assertTrue(renamed["success"])
            self.assertTrue((folder_path / "final.txt").exists())
            self.assertFalse(src_file.exists())

            # Copy file
            copied = copy_file(str(folder_path / "final.txt"), str(folder_path / "copied.txt"))
            self.assertTrue(copied["success"])
            self.assertTrue((folder_path / "copied.txt").exists())

            # Search ambiguous file
            (folder_path / "doc_1.txt").write_text("1")
            (folder_path / "doc_2.txt").write_text("2")
            search_res = search_file("doc_", root_dir=str(folder_path))
            self.assertTrue(search_res.get("ambiguous", False))
            self.assertIn("Which one do you mean", search_res["message"])

            # Delete file
            del_res = delete_file(str(folder_path / "copied.txt"))
            self.assertTrue(del_res["success"])
            self.assertFalse((folder_path / "copied.txt").exists())

            # Delete folder
            del_folder = delete_folder(str(folder_path))
            self.assertTrue(del_folder["success"])
            self.assertFalse(folder_path.exists())

    def test_system_policy_requires_confirmation(self):
        # Unconfirmed calls must fail and request confirmation
        sd = shutdown(confirm=False)
        self.assertFalse(sd["success"])
        self.assertTrue(sd["requires_confirmation"])

        rst = restart(confirm=False)
        self.assertFalse(rst["success"])
        self.assertTrue(rst["requires_confirmation"])

        slp = sleep(confirm=False)
        self.assertFalse(slp["success"])
        self.assertTrue(slp["requires_confirmation"])

    def test_terminal_policy_classification(self):
        # Safe commands
        lvl, _ = classify_command("dir")
        self.assertEqual(lvl, "safe")
        lvl, _ = classify_command("git status")
        self.assertEqual(lvl, "safe")

        # Confirmation required
        lvl, _ = classify_command("npm install -g something")
        self.assertEqual(lvl, "requires_confirmation")
        lvl, _ = classify_command("pip install requests")
        self.assertEqual(lvl, "requires_confirmation")

        # Blocked destructive commands
        lvl, _ = classify_command("format C:")
        self.assertEqual(lvl, "blocked")
        lvl, _ = classify_command("rmdir /s /q c:\\")
        self.assertEqual(lvl, "blocked")

        # Blocked command should not execute
        res = run_command("format C:")
        self.assertFalse(res["success"])
        self.assertTrue(res.get("blocked", False))

    def test_screen_and_input_tools(self):
        elem = find_ui_element("Start")
        self.assertIn("element", elem)

        with patch("ctypes.windll.user32.GetSystemMetrics", side_effect=[1920, 1080, 1]):
            scr = inspect_screen()
            self.assertTrue(scr["success"])
            self.assertEqual(scr["width"], 1920)
            self.assertEqual(scr["height"], 1080)


if __name__ == "__main__":
    unittest.main()
