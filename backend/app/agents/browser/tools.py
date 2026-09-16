from __future__ import annotations

import html
import re
import urllib.parse
import urllib.error
import urllib.request
import webbrowser
from typing import Any, Dict, List


_SEARCH_URL = "https://html.duckduckgo.com/html/?q={}"


def _result(success: bool, message: str, verified: bool = False, **data: Any) -> Dict[str, Any]:
    return {"success": success, "verified": verified, "message": message, **data}


def _fetch(url: str, timeout: float = 10) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "EVI/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _normalize_url(target: str) -> str:
    target = target.strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", target, re.I):
        return "https://" + target
    return target


def open_url(target: str) -> Dict[str, Any]:
    if not target.strip():
        return _result(False, "I need a URL to open.")
    url = _normalize_url(target)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or any(character.isspace() for character in url):
        return _result(False, "That URL is not valid.", url=url)
    try:
        opened = webbrowser.open(url, new=2)
        return _result(bool(opened), "The page was opened successfully." if opened else "I couldn't open that page.", bool(opened), url=url)
    except (OSError, ValueError):
        return _result(False, "I couldn't open that page.", url=url)


def web_search(query: str) -> Dict[str, Any]:
    if not query.strip():
        return _result(False, "I need a search query.", results=[])
    try:
        document = _fetch(_SEARCH_URL.format(urllib.parse.quote_plus(query)))
        results: List[Dict[str, str]] = []
        pattern = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
        for raw_url, raw_title in pattern.findall(document)[:10]:
            results.append({"title": html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip(), "url": html.unescape(raw_url)})
        return _result(bool(results), f"Found {len(results)} results." if results else "I couldn't find search results.", bool(results), query=query, results=results)
    except (OSError, ValueError, urllib.error.URLError):
        return _result(False, "The web search is unavailable right now.", query=query, results=[])


def read_page(url: str) -> Dict[str, Any]:
    try:
        source = _fetch(_normalize_url(url))
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", source, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        return _result(True, "The page was read successfully.", True, url=_normalize_url(url), text=text[:20000])
    except (OSError, ValueError, urllib.error.URLError):
        return _result(False, "I couldn't read that page.", url=url, text="")


def get_title(url: str) -> Dict[str, Any]:
    page = read_page(url)
    if not page["success"]:
        return page
    try:
        source = _fetch(_normalize_url(url))
        match = re.search(r"<title[^>]*>(.*?)</title>", source, flags=re.I | re.S)
        title = html.unescape(re.sub(r"\s+", " ", match.group(1))).strip() if match else ""
        return _result(bool(title), "The page title was found." if title else "I couldn't find a page title.", bool(title), url=_normalize_url(url), title=title)
    except (OSError, ValueError, urllib.error.URLError):
        return _result(False, "I couldn't get the page title.", url=url, title="")


def get_links(url: str) -> Dict[str, Any]:
    try:
        source = _fetch(_normalize_url(url))
        links = []
        for raw_url, raw_label in re.findall(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", source, re.I | re.S):
            label = html.unescape(re.sub(r"<[^>]+>", "", raw_label)).strip()
            if label:
                links.append({"text": label, "url": urllib.parse.urljoin(_normalize_url(url), html.unescape(raw_url))})
        return _result(True, f"Found {len(links)} links.", True, url=_normalize_url(url), links=links[:100])
    except (OSError, ValueError, urllib.error.URLError):
        return _result(False, "I couldn't get links from that page.", url=url, links=[])


def unsupported(action: str) -> Dict[str, Any]:
    return _result(False, f"Browser action '{action}' requires an accessibility browser adapter and is not enabled yet.")
