# ntfy Transport Behavior

## 2026-02-24: Upload mode regression on ntfy.sh
- Verified with both `requests` and `curl` that posting with filename headers (`X-Filename` and `Filename`) consistently returns `HTTP 500` from `ntfy.sh`.
- Regular message posts (plain body, no upload headers) return `HTTP 200` for the same topics.
- Send logic was changed to avoid upload mode and send UTF-8 message bodies directly, because upload-mode retries/fallbacks would only mask the upstream failure.
