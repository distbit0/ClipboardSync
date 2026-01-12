from pathlib import Path

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

    assert _is_urls_and_whitespace_only(text, urls) is True


def test_urls_only_rejects_extra_text(tmp_path: Path) -> None:
    local_file = tmp_path / "tics_clean.pdf"
    local_file.write_text("content")

    text = f"file://{local_file}\nnot-a-url"
    urls = [str(local_file)]

    assert _is_urls_and_whitespace_only(text, urls) is False
