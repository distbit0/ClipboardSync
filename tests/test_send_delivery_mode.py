from types import SimpleNamespace

import send


def test_no_convert_sends_single_non_url_message(monkeypatch) -> None:
    captured_payloads: list[bytes] = []

    dummy_lineate = SimpleNamespace(find_urls_in_text=lambda _text: [])
    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(send.pyperclip, "paste", lambda: "hello world")

    def fake_post(url, data, timeout):
        assert url == "https://ntfy.sh/topic-name"
        assert timeout == 20
        captured_payloads.append(data)
        return SimpleNamespace(status_code=200, text="ok")

    monkeypatch.setattr(send.requests, "post", fake_post)

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=False)

    assert captured_payloads == [b"hello world"]


def test_urls_only_conversion_splits_into_multiple_messages(monkeypatch) -> None:
    captured_payloads: list[bytes] = []

    dummy_lineate = SimpleNamespace(
        utilities=SimpleNamespace(set_default_summarise=lambda _enabled: None),
        find_urls_in_text=lambda _text: [
            "https://example.com/one",
            "https://example.com/two",
            "https://example.com/three",
        ],
    )

    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(
        send.pyperclip,
        "paste",
        lambda: "https://example.com/one\nhttps://example.com/two\nhttps://example.com/three",
    )
    monkeypatch.setattr(
        send,
        "convert_links_in_text",
        lambda _text: (
            "https://converted.example/aaa\nhttps://converted.example/bbb\nhttps://converted.example/ccc",
            [
                "https://converted.example/aaa",
                "https://converted.example/bbb",
                "https://converted.example/ccc",
            ],
        ),
    )
    monkeypatch.setattr(send, "MAX_NON_FILE_MESSAGE_BYTES", 60)

    def fake_post(url, data, timeout):
        assert url == "https://ntfy.sh/topic-name"
        assert timeout == 20
        captured_payloads.append(data)
        return SimpleNamespace(status_code=200, text="ok")

    monkeypatch.setattr(send.requests, "post", fake_post)

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=True)

    assert captured_payloads == [
        b"https://converted.example/aaa\nhttps://converted.example/bbb",
        b"https://converted.example/ccc",
    ]


def test_oversized_non_url_content_fails_and_alerts(monkeypatch) -> None:
    desktop_alerts: list[str] = []

    dummy_lineate = SimpleNamespace(find_urls_in_text=lambda _text: [])
    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(send.pyperclip, "paste", lambda: "this content is too large")
    monkeypatch.setattr(send, "MAX_NON_FILE_MESSAGE_BYTES", 8)
    monkeypatch.setattr(send, "_show_desktop_error", desktop_alerts.append)

    def fake_post(_url, _data, _timeout):
        raise AssertionError("requests.post should not be called for oversized non-URL content")

    monkeypatch.setattr(send.requests, "post", fake_post)

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=False)

    assert desktop_alerts == [
        "Message too large to send without file attachment. Trim content or send URLs only."
    ]
