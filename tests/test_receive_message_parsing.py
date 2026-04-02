import pytest

from receive import (
    ATTACHMENT_NOTICE,
    _build_ws_url,
    _load_last_processed_message_id,
    _store_last_processed_message_id,
    resolve_message_text,
)


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


def test_build_ws_url_includes_since_when_message_id_exists():
    assert _build_ws_url("topic-name", "abc123") == "wss://ntfy.sh/topic-name/ws?since=abc123"


def test_build_ws_url_omits_since_without_message_id():
    assert _build_ws_url("topic-name", None) == "wss://ntfy.sh/topic-name/ws"


def test_receive_state_round_trips_last_processed_message_id(tmp_path):
    state_path = tmp_path / "receive_state.json"

    _store_last_processed_message_id("topic-a", "msg-1", state_path)
    _store_last_processed_message_id("topic-b", "msg-2", state_path)

    assert _load_last_processed_message_id("topic-a", state_path) == "msg-1"
    assert _load_last_processed_message_id("topic-b", state_path) == "msg-2"
    assert _load_last_processed_message_id("topic-c", state_path) is None
