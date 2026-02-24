# ntfy Transport Behavior

## 2026-02-24: Upload mode regression on ntfy.sh
- Verified with both `requests` and `curl` that posting with filename headers (`X-Filename` and `Filename`) consistently returns `HTTP 500` from `ntfy.sh`.
- Regular message posts (plain body, no upload headers) return `HTTP 200` for the same topics.

## 2026-02-24: URL chunking strategy
- Since attachment uploads are failing upstream, URL-only payloads are sent as multiple regular messages, split by URL boundaries.
- Non-URL payloads are not split. If non-URL content exceeds the safe non-file message size, sending fails and a desktop alert is shown.
