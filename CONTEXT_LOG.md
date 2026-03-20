# ntfy Transport Behavior

## 2026-02-24: Upload mode regression on ntfy.sh
- Verified with both `requests` and `curl` that posting with filename headers (`X-Filename` and `Filename`) consistently returns `HTTP 500` from `ntfy.sh`.
- Regular message posts (plain body, no upload headers) return `HTTP 200` for the same topics.

## 2026-03-02: Durable URL queue strategy
- URL-only sends now use a persistent shared queue from `lineate/src/persistent_url_queue.py` to survive interruptions and continue on later runs.
- URL jobs are checkpointed one URL at a time, and a URL is only removed from the queue after an HTTP 200 send succeeds.
- Queue jobs include a workflow marker (`send_ntfy_raw` vs `send_ntfy_convert`) so replay preserves processing intent.
- `NTFY_SEND_TOPIC` is resolved at send time for each queued URL attempt, so queued backlog follows current environment configuration.
- `send.py` now attempts queue draining on every run before handling the current clipboard payload, so pending URL backlog progresses even when the current clipboard content is plain text.

## 2026-03-19: URL-only routing consistency with lineate
- `send.py` now reuses `lineate._count_non_url_words` when deciding whether clipboard content is URLs-only, instead of maintaining a separate raw-text stripping heuristic.
- This keeps `send.py` aligned with `lineate` for normalized wrappers such as LeechBlock delayed URLs (`chrome-extension://.../delayed.html?...`), which otherwise look like mixed text even when they should be treated as a single URL.

## 2026-03-20: ntfy 429 retry semantics
- `send.py` now retries `HTTP 429` indefinitely in-process instead of treating rate limiting as a hard failure.
- The retry delay honors ntfy's `Retry-After` header when present; otherwise it logs that the header was missing/invalid and uses explicit exponential backoff.
- This lives in the shared plain-message send path, so queued URL sends driven by the `lineate` integration inherit the same behavior automatically.

## 2026-03-20: lineate-owned URL batch normalization
- `send.py` now delegates queue-bound URL batch normalization to `lineate` via `_expand_batch_urls(...)` and `_rewrite_pending_playlist_jobs(...)` instead of carrying its own notion of special URL shapes.
- This keeps durable ntfy delivery aligned with `lineate` for playlist expansion and any future batch-boundary URL rewrites, rather than duplicating routing policy in two repos.
