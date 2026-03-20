from types import SimpleNamespace

import send


def test_no_convert_sends_single_non_url_message(monkeypatch) -> None:
    captured_payloads: list[bytes] = []

    dummy_lineate = SimpleNamespace(
        find_urls_in_text=lambda _text: [],
        _count_non_url_words=lambda _text, _urls: 2,
    )
    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(send, "_drain_pending_url_jobs", lambda _lineate: [])
    monkeypatch.setattr(send.pyperclip, "paste", lambda: "hello world")

    def fake_post(url, data, timeout):
        assert url == "https://ntfy.sh/topic-name"
        assert timeout == 20
        captured_payloads.append(data)
        return SimpleNamespace(status_code=200, text="ok")

    monkeypatch.setattr(send.requests, "post", fake_post)

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=False)

    assert captured_payloads == [b"hello world"]


def test_send_plain_messages_retries_429_until_success(monkeypatch) -> None:
    attempted_payloads: list[bytes] = []
    sleep_durations: list[int] = []
    responses = iter(
        [
            SimpleNamespace(status_code=429, text="slow down", headers={"Retry-After": "3"}),
            SimpleNamespace(status_code=200, text="ok", headers={}),
        ]
    )

    def fake_post(url, data, timeout):
        assert url == "https://ntfy.sh/topic-name"
        assert timeout == 20
        attempted_payloads.append(data)
        return next(responses)

    monkeypatch.setattr(send.requests, "post", fake_post)
    monkeypatch.setattr(send.time, "sleep", sleep_durations.append)

    assert send._send_plain_messages("https://ntfy.sh/topic-name", ["hello world"]) is True
    assert attempted_payloads == [b"hello world", b"hello world"]
    assert sleep_durations == [3]


def test_urls_only_conversion_routes_to_queue_delivery(monkeypatch) -> None:
    queue_calls: list[tuple[list[str], bool]] = []

    dummy_lineate = SimpleNamespace(
        utilities=SimpleNamespace(set_default_summarise=lambda _enabled: None),
        find_urls_in_text=lambda _text: [
            "https://example.com/one",
            "https://example.com/two",
            "https://example.com/three",
        ],
        _count_non_url_words=lambda _text, _urls: 0,
    )

    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(send, "_drain_pending_url_jobs", lambda _lineate: [])
    monkeypatch.setattr(
        send.pyperclip,
        "paste",
        lambda: "https://example.com/one\nhttps://example.com/two\nhttps://example.com/three",
    )
    monkeypatch.setattr(
        send,
        "_enqueue_and_send_url_jobs",
        lambda _lineate, urls, convert: queue_calls.append((urls, convert)),
    )

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=True)

    assert queue_calls == [
        (
            [
                "https://example.com/one",
                "https://example.com/two",
                "https://example.com/three",
            ],
            True,
        )
    ]


def test_leechblock_wrapped_single_link_routes_to_queue_delivery(monkeypatch) -> None:
    queue_calls: list[tuple[list[str], bool]] = []
    wrapped_url = (
        "chrome-extension://blaaajhemilngeeffpbfkdjjoefldkok/"
        "delayed.html?4&https://www.greaterwrong.com/posts/qqcQN2YBc5jFpehbm/"
        "sparks-of-rsi-1"
    )
    unwrapped_url = "https://www.greaterwrong.com/posts/qqcQN2YBc5jFpehbm/sparks-of-rsi-1"

    dummy_lineate = SimpleNamespace(
        utilities=SimpleNamespace(set_default_summarise=lambda _enabled: None),
        find_urls_in_text=lambda _text: [unwrapped_url],
        _count_non_url_words=lambda _text, _urls: 0,
    )

    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(send, "_drain_pending_url_jobs", lambda _lineate: [])
    monkeypatch.setattr(send.pyperclip, "paste", lambda: wrapped_url)
    monkeypatch.setattr(
        send,
        "_enqueue_and_send_url_jobs",
        lambda _lineate, urls, convert: queue_calls.append((urls, convert)),
    )

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=True)

    assert queue_calls == [([unwrapped_url], True)]


def test_send_notification_drains_pending_queue_before_non_url_send(monkeypatch) -> None:
    captured_payloads: list[bytes] = []
    drained_lineate_objects = []

    dummy_lineate = SimpleNamespace(
        find_urls_in_text=lambda _text: [],
        _count_non_url_words=lambda _text, _urls: 2,
    )
    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(send.pyperclip, "paste", lambda: "hello world")
    monkeypatch.setattr(
        send, "_drain_pending_url_jobs", lambda lineate: drained_lineate_objects.append(lineate)
    )

    def fake_post(url, data, timeout):
        assert url == "https://ntfy.sh/topic-name"
        assert timeout == 20
        captured_payloads.append(data)
        return SimpleNamespace(status_code=200, text="ok")

    monkeypatch.setattr(send.requests, "post", fake_post)

    send.send_notification_to_phone("topic-name", use_selected_text=False, convert=False)

    assert drained_lineate_objects == [dummy_lineate]
    assert captured_payloads == [b"hello world"]


def test_enqueue_and_send_url_jobs_uses_fresh_topic_per_claim(monkeypatch) -> None:
    captured_payloads: list[tuple[str, list[str]]] = []

    class DummyQueue:
        def __init__(self):
            self.jobs: list[dict] = []

        def create_url_job(self, url, workflow, payload):
            return {"url": url, "workflow": workflow, "payload": payload}

        def enqueue_jobs(self, _queue_name, jobs):
            self.jobs.extend(jobs)
            return len(jobs)

        def drain_queue(self, _queue_name, process_job):
            outputs = []
            for index, job in enumerate(self.jobs, start=1):
                claimed = {
                    "id": str(index),
                    "url": job["url"],
                    "workflow": job["workflow"],
                    "payload": job["payload"],
                }
                outputs.append(process_job(claimed))
            return outputs, "drained"

    dummy_lineate = SimpleNamespace(persistent_url_queue=DummyQueue())
    monkeypatch.setenv("NTFY_SEND_TOPIC", "topic-a")

    def fake_send_plain_messages(api_url, payload_messages):
        captured_payloads.append((api_url, payload_messages))
        if len(captured_payloads) == 1:
            monkeypatch.setenv("NTFY_SEND_TOPIC", "topic-b")
        return True

    monkeypatch.setattr(send, "_send_plain_messages", fake_send_plain_messages)

    delivered = send._enqueue_and_send_url_jobs(
        dummy_lineate,
        ["https://example.com/one", "https://example.com/two"],
        convert=False,
    )

    assert delivered == ["https://example.com/one", "https://example.com/two"]
    assert captured_payloads == [
        ("https://ntfy.sh/topic-a", ["https://example.com/one"]),
        ("https://ntfy.sh/topic-b", ["https://example.com/two"]),
    ]


def test_enqueue_and_send_url_jobs_retries_429_and_still_delivers(monkeypatch) -> None:
    sleep_durations: list[int] = []
    attempted_payloads: list[bytes] = []
    responses = iter(
        [
            SimpleNamespace(status_code=429, text="slow down", headers={}),
            SimpleNamespace(status_code=200, text="ok", headers={}),
        ]
    )

    class DummyQueue:
        def __init__(self):
            self.jobs: list[dict] = []

        def create_url_job(self, url, workflow, payload):
            return {"url": url, "workflow": workflow, "payload": payload}

        def enqueue_jobs(self, _queue_name, jobs):
            self.jobs.extend(jobs)
            return len(jobs)

        def drain_queue(self, _queue_name, process_job):
            outputs = []
            for index, job in enumerate(self.jobs, start=1):
                claimed = {
                    "id": str(index),
                    "url": job["url"],
                    "workflow": job["workflow"],
                    "payload": job["payload"],
                }
                outputs.append(process_job(claimed))
            return outputs, "drained"

    def fake_post(url, data, timeout):
        assert url == "https://ntfy.sh/topic-name"
        assert timeout == 20
        attempted_payloads.append(data)
        return next(responses)

    dummy_lineate = SimpleNamespace(persistent_url_queue=DummyQueue())
    monkeypatch.setenv("NTFY_SEND_TOPIC", "topic-name")
    monkeypatch.setattr(send.requests, "post", fake_post)
    monkeypatch.setattr(send.time, "sleep", sleep_durations.append)

    delivered = send._enqueue_and_send_url_jobs(
        dummy_lineate,
        ["https://example.com/one"],
        convert=False,
    )

    assert delivered == ["https://example.com/one"]
    assert attempted_payloads == [b"https://example.com/one", b"https://example.com/one"]
    assert sleep_durations == [1]


def test_enqueue_and_send_url_jobs_uses_workflow_from_queued_job(monkeypatch) -> None:
    sent_payloads: list[str] = []
    converted_urls: list[str] = []

    class DummyQueue:
        def __init__(self):
            self.jobs: list[dict] = [
                {
                    "url": "https://example.com/needs-convert",
                    "workflow": send.SEND_CONVERT_WORKFLOW,
                    "payload": {"convert": True},
                }
            ]

        def create_url_job(self, url, workflow, payload):
            return {"url": url, "workflow": workflow, "payload": payload}

        def enqueue_jobs(self, _queue_name, jobs):
            self.jobs.extend(jobs)
            return len(jobs)

        def drain_queue(self, _queue_name, process_job):
            outputs = []
            for index, job in enumerate(self.jobs, start=1):
                claimed = {
                    "id": str(index),
                    "url": job["url"],
                    "workflow": job["workflow"],
                    "payload": job["payload"],
                }
                outputs.append(process_job(claimed))
            return outputs, "drained"

    def fake_process_url(url, **_kwargs):
        converted = f"https://converted.example/{url.rsplit('/', 1)[-1]}"
        converted_urls.append(converted)
        return converted

    dummy_lineate = SimpleNamespace(
        persistent_url_queue=DummyQueue(),
        process_url=fake_process_url,
    )
    monkeypatch.setenv("NTFY_SEND_TOPIC", "topic-x")
    monkeypatch.setattr(
        send, "_send_plain_messages", lambda _api_url, payloads: sent_payloads.append(payloads[0]) or True
    )

    delivered = send._enqueue_and_send_url_jobs(
        dummy_lineate, ["https://example.com/raw"], convert=False
    )

    assert delivered == [
        "https://converted.example/needs-convert",
        "https://example.com/raw",
    ]
    assert converted_urls == ["https://converted.example/needs-convert"]
    assert sent_payloads == [
        "https://converted.example/needs-convert",
        "https://example.com/raw",
    ]


def test_oversized_non_url_content_fails_and_alerts(monkeypatch) -> None:
    desktop_alerts: list[str] = []

    dummy_lineate = SimpleNamespace(
        find_urls_in_text=lambda _text: [],
        _count_non_url_words=lambda _text, _urls: 4,
    )
    monkeypatch.setattr(send, "_configure_logging", lambda: None)
    monkeypatch.setattr(send, "_load_lineate", lambda: dummy_lineate)
    monkeypatch.setattr(send, "_drain_pending_url_jobs", lambda _lineate: [])
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
