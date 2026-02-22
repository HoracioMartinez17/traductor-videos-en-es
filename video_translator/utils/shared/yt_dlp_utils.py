from typing import Any, Callable, Optional, TypeVar, cast

from yt_dlp import YoutubeDL


T = TypeVar("T")
BROWSERS = ("chrome", "edge", "firefox")


def _run_with_optional_browser_cookies(
    ydl_opts: dict[str, Any],
    executor: Callable[[dict[str, Any]], T],
    try_browser_cookies: bool = True,
) -> tuple[T, Optional[str]]:
    if try_browser_cookies:
        for browser in BROWSERS:
            try:
                opts_with_cookies = ydl_opts.copy()
                opts_with_cookies["cookiesfrombrowser"] = (browser,)
                return executor(opts_with_cookies), browser
            except Exception:
                continue

    return executor(ydl_opts), None


def extract_info_with_fallback(
    url: str,
    ydl_opts: dict[str, Any],
    download: bool,
    try_browser_cookies: bool = True,
) -> tuple[Any, Optional[str], Optional[str]]:
    def _execute(options: dict[str, Any]) -> tuple[Any, Optional[str]]:
        with YoutubeDL(cast(Any, options)) as ydl:
            info = ydl.extract_info(url, download=download)
            filename = ydl.prepare_filename(info) if info else None
            return info, filename

    (info, filename), browser = _run_with_optional_browser_cookies(
        ydl_opts,
        _execute,
        try_browser_cookies=try_browser_cookies,
    )
    return info, filename, browser


def download_with_fallback(
    url: str,
    ydl_opts: dict[str, Any],
    try_browser_cookies: bool = True,
) -> Optional[str]:
    def _execute(options: dict[str, Any]) -> None:
        with YoutubeDL(cast(Any, options)) as ydl:
            ydl.download([url])

    _, browser = _run_with_optional_browser_cookies(
        ydl_opts,
        _execute,
        try_browser_cookies=try_browser_cookies,
    )
    return browser
