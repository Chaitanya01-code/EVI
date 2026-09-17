from app.phase4.computer.controller import DesktopAutomationController


def test_open_application_returns_structured_result():
    controller = DesktopAutomationController()
    result = controller.open_application("Notepad")
    assert result["success"] is True
    assert result["application"] == "Notepad"


def test_window_inspection_returns_window_details():
    controller = DesktopAutomationController()
    result = controller.inspect_window("Notepad")
    assert result["success"] is True
    assert "window" in result
