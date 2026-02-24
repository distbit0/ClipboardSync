from types import SimpleNamespace

import send


def test_no_convert_sends_plain_text_bytes(monkeypatch) -> None:
    captured: dict = {}

    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: object())
    monkeypatch.setattr(send.pyperclip, "paste", lambda: "hello world")

    def fake_post(url, data, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        return SimpleNamespace(status_code=200, text="ok")

    monkeypatch.setattr(send.requests, "post", fake_post)

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=False)

    assert captured["url"] == "https://ntfy.sh/topic-name"
    assert captured["data"] == b"hello world"
    assert captured["timeout"] == 20


def test_urls_only_conversion_sends_plain_text_bytes(monkeypatch) -> None:
    captured: dict = {}

    dummy_lineate = SimpleNamespace(
        utilities=SimpleNamespace(set_default_summarise=lambda _enabled: None),
        find_urls_in_text=lambda _text: [
            "https://example.com/one",
            "https://example.com/two",
        ],
    )

    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(
        send.pyperclip,
        "paste",
        lambda: "https://example.com/one\nhttps://example.com/two",
    )
    monkeypatch.setattr(
        send,
        "convert_links_in_text",
        lambda _text: (
            "https://converted.example/a\nhttps://converted.example/b",
            ["https://converted.example/a", "https://converted.example/b"],
        ),
    )

    def fake_post(url, data, timeout):
        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        return SimpleNamespace(status_code=200, text="ok")

    monkeypatch.setattr(send.requests, "post", fake_post)

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=True)

    assert captured["url"] == "https://ntfy.sh/topic-name"
    assert captured["data"] == b"https://converted.example/a\nhttps://converted.example/b"
    assert captured["timeout"] == 20
