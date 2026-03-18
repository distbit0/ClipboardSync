from pathlib import Path
from types import SimpleNamespace

from send import _is_urls_and_whitespace_only


def test_urls_only_with_file_scheme(tmp_path: Path) -> None:
    local_file = tmp_path / "tics_clean.pdf"
    local_file.write_text("content")

    text = (
        "https://example.com/a\n"
        "https://example.com/b\n"
        f"file://{local_file}\n"
    )
    urls = [
        "https://example.com/a",
        "https://example.com/b",
        str(local_file),
    ]

    lineate = SimpleNamespace(_count_non_url_words=lambda _text, _urls: 0)

    assert _is_urls_and_whitespace_only(lineate, text, urls) is True


def test_urls_only_rejects_extra_text(tmp_path: Path) -> None:
    local_file = tmp_path / "tics_clean.pdf"
    local_file.write_text("content")

    text = f"file://{local_file}\nnot-a-url"
    urls = [str(local_file)]
    lineate = SimpleNamespace(_count_non_url_words=lambda _text, _urls: 1)

    assert _is_urls_and_whitespace_only(lineate, text, urls) is False


def test_urls_only_accepts_leechblock_wrapped_url() -> None:
    text = (
        "chrome-extension://blaaajhemilngeeffpbfkdjjoefldkok/"
        "delayed.html?4&https://www.greaterwrong.com/posts/qqcQN2YBc5jFpehbm/"
        "sparks-of-rsi-1"
    )
    urls = ["https://www.greaterwrong.com/posts/qqcQN2YBc5jFpehbm/sparks-of-rsi-1"]
    lineate = SimpleNamespace(_count_non_url_words=lambda _text, _urls: 0)

    assert _is_urls_and_whitespace_only(lineate, text, urls) is True
