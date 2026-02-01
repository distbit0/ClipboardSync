import pytest

from receive import ATTACHMENT_NOTICE, resolve_message_text


def test_resolve_message_text_returns_plain_message():
    data = {"message": "hello world"}
    assert resolve_message_text(data, lambda _: "unused") == "hello world"


def test_resolve_message_text_returns_none_without_message():
    data = {"event": "open"}
    assert resolve_message_text(data, lambda _: "unused") is None


def test_resolve_message_text_attachment_fetches_payload():
    seen = {}

    def fetcher(attachment_id: str) -> str:
        seen["id"] = attachment_id
        return "file contents"

    data = {"message": ATTACHMENT_NOTICE, "id": "abc123"}
    assert resolve_message_text(data, fetcher) == "file contents"
    assert seen["id"] == "abc123"


def test_resolve_message_text_attachment_requires_id():
    data = {"message": ATTACHMENT_NOTICE}
    with pytest.raises(ValueError):
        resolve_message_text(data, lambda _: "unused")
