---
name: alpaca-broker-rate-limits-resilience
description: Make Alpaca API clients resilient — rate-limit header handling, HTTP 429 backoff, exponential retry, bounded concurrency/worker pools, pagination loops, batch sizing, and timeouts. Use when building robust REST clients, bulk/cron jobs, or reconciliation sweeps against Alpaca in any language.
---

# Alpaca — Rate Limits & Resilience

Alpaca's APIs are rate-limited and occasionally flaky under load. Any client that does more than a handful of calls — especially bulk jobs, backfills, and reconciliation sweeps — needs disciplined retry, backoff, and concurrency control. These patterns are transport-level and apply in any language.

> Read `alpaca-broker-integration` first.

## 1. Rate-limit headers — read them on every response

Alpaca returns standard headers:

| Header | Meaning |
|--------|---------|
| `X-RateLimit-Limit` | requests allowed in the window |
| `X-RateLimit-Remaining` | requests left in the current window |
| `X-RateLimit-Reset` | **unix timestamp (seconds)** when the window resets |

**Parse them on every response, not just on errors.** Two uses:
- **Proactive:** when `Remaining` drops below a threshold (e.g. ≤ 50), log a warning and/or slow down — you're about to get throttled.
- **Reactive:** on `429`, use `Reset` to wait exactly until the window opens.

> Limits vary by endpoint and plan; market-data limits differ from broker limits. Don't hardcode a number — react to the headers.

## 2. The retry loop (pseudocode)

```
MAX_ATTEMPTS = 10
INITIAL_DELAY_MS = 1000

for attempt in 1..MAX_ATTEMPTS:
    res = http(request)                      # with a sane timeout (see §5)
    remaining, reset_at = parse_rate_headers(res.headers)
    if remaining <= 50: log_warn("approaching rate limit", reset_at)

    if res.status == 429:
        # wait until the window resets, plus a small buffer
        wait = (reset_at - now()) if reset_at else INITIAL_DELAY_MS * 2^(attempt-1)
        sleep(max(0, wait) + 1000)           # +1s buffer past reset
        continue

    if res.status in (500, 502, 503, 504) or network_error:
        sleep(INITIAL_DELAY_MS * 2^(attempt-1))   # exponential backoff
        continue

    return res                                # success or non-retryable 4xx
raise last_error
```

Key points:
- **On `429`, wait until `X-RateLimit-Reset` + a ~1s buffer** — don't blindly exponential-backoff when the API told you exactly when to retry.
- **Exponential backoff** (`base * 2^(attempt-1)`) for network errors and 5xx. With base 1s and 10 attempts the tail is minutes — fine for background jobs, too slow for user-facing calls (use fewer attempts there).
- **Don't retry non-retryable 4xx** (`400`/`403`/`422`) — those won't fix themselves; surface them.
- Optionally add **jitter** to backoff to avoid thundering-herd when many workers retry together.

## 3. Bounded concurrency

Parallelism speeds bulk jobs but is the fastest way to hit limits. Use a **fixed worker pool**, not unbounded fan-out.

- Start small (e.g. **5–8 concurrent requests**) and tune against the rate-limit headers. A real lesson from production: a pool was *reduced* from 10 → 5 to ease both Alpaca and downstream-DB load.
- Cache per-entity reads **within a run** (e.g. an account's buying power, or a per-account transfer list) so you don't refetch the same thing across items in a batch.
- For per-item throttling, a small fixed sleep between calls (e.g. 100ms) is a crude-but-effective floor when you can't easily coordinate a pool.

## 4. Pagination loops

List endpoints page forward with a token — never assume one response is complete.

- **Activities** (`/v1/accounts/activities`): page via the `X-Next-Page-Token` response header; loop until it's empty. Use `page_size` (≤100) and a `direction`.
- **Market-data bars** (`/v2/stocks/bars`): page via `next_page_token` in the body → pass back as `page_token`. Remember `limit` counts across all symbols and results sort by symbol-then-time, so **a single page may contain only the first symbol(s)** — keep paging.
- Wrap each page fetch in the retry loop from §2.

```
token = null
loop:
    page = fetch(url + (token ? "&page_token="+token : ""))   # via retry loop
    accumulate(page.items)
    token = page.next_token            # header or body, per endpoint
    if not token: break
```

## 5. Timeouts & batch sizing

- **Always set an HTTP timeout** (e.g. 15–30s). A hung connection without a timeout stalls a whole worker pool. (SSE streams are the exception — they're meant to stay open; see `alpaca-broker-sse-events`.)
- Use a **shared HTTP client / connection pool** rather than constructing one per request, so keep-alive and connection reuse work.
- When writing reconciliation results to your own store, **chunk bulk inserts** (e.g. 500 rows per statement) to stay under DB statement-size limits and keep transactions reasonable.

## 6. Resilience checklist for a bulk/cron job

- [ ] Rate-limit headers parsed every response; proactive warn near the limit.
- [ ] `429` → wait until `X-RateLimit-Reset` + buffer.
- [ ] Exponential backoff (+ jitter) for 5xx/network; capped attempts.
- [ ] Non-retryable 4xx surfaced, not retried.
- [ ] Bounded worker pool; per-run caching of repeated reads.
- [ ] Pagination loop until the token is empty.
- [ ] HTTP timeout on every call; shared client.
- [ ] Bulk DB writes chunked and idempotent (upsert) — see `alpaca-broker-reconciliation-idempotency`.
- [ ] Structured logging with a trace/correlation ID per item for debugging partial failures.

**Related skills:** safe re-runs of jobs → `alpaca-broker-reconciliation-idempotency`; the heal/poll jobs that use these patterns → `alpaca-broker-reconciliation-idempotency`; market-data pagination specifics → `alpaca-broker-market-data`.
