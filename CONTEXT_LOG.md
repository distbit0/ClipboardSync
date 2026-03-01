# ntfy Transport Behavior

## 2026-02-24: Upload mode regression on ntfy.sh
- Verified with both `requests` and `curl` that posting with filename headers (`X-Filename` and `Filename`) consistently returns `HTTP 500` from `ntfy.sh`.
- Regular message posts (plain body, no upload headers) return `HTTP 200` for the same topics.

## 2026-03-02: Durable URL queue strategy
- URL-only sends now use a persistent shared queue from `lineate/src/persistent_url_queue.py` to survive interruptions and continue on later runs.
- URL jobs are checkpointed one URL at a time, and a URL is only removed from the queue after an HTTP 200 send succeeds.
- Queue jobs include a workflow marker (`send_ntfy_raw` vs `send_ntfy_convert`) so replay preserves processing intent.
- `NTFY_SEND_TOPIC` is resolved at send time for each queued URL attempt, so queued backlog follows current environment configuration.
