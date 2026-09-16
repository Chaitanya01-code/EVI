from __future__ import annotations

from typing import Any, Callable, Dict

from app.agents.browser.tools import get_links, get_title, open_url, read_page, unsupported, web_search


class BrowserToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Dict[str, Any]]] = {
            "open_url": open_url,
            "navigate": open_url,
            "search": web_search,
            "web_search": web_search,
            "read_page": read_page,
            "get_title": get_title,
            "get_links": get_links,
            "back": lambda: unsupported("back"),
            "forward": lambda: unsupported("forward"),
            "refresh": lambda: unsupported("refresh"),
            "new_tab": lambda: unsupported("new_tab"),
        }

    def resolve(self, action: str) -> Callable[..., Dict[str, Any]] | None:
        return self._tools.get(action)

    def list_tools(self) -> list[str]:
        return sorted(self._tools)


browser_tools = BrowserToolRegistry()
