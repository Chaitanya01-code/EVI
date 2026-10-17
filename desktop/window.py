from __future__ import annotations

from typing import Any, Dict


class EVIWindow:
    """Native PyWebView window for the existing local EVI frontend."""

    def __init__(self, url: str, config: Dict[str, Any]) -> None:
        try:
            import webview
        except ImportError as error:
            raise RuntimeError("PyWebView is required. Install it with: python -m pip install pywebview") from error

        window_config = config.get("window", {})
        self._webview = webview
        self._window = webview.create_window(
            title=str(window_config.get("title", "EVI")),
            url=url,
            width=int(window_config.get("width", 1280)),
            height=int(window_config.get("height", 800)),
            resizable=bool(window_config.get("resizable", True)),
            fullscreen=False,
            confirm_close=False,
        )

    def run(self) -> None:
        self._webview.start()

    def close(self) -> None:
        self._window.destroy()
