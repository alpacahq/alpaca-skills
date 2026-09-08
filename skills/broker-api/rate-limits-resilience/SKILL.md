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
- **Proactive:** slow down as `Remaining` falls toward zero, rather than waiting to be throttled. Any warning threshold you pick is your own starting point, derived from `Limit` — Alpaca publishes none.
- **Reactive:** on `429`, use `Reset` to wait exactly until the window opens.

> Broker limits are applied at the **correspondent level** — across your whole integration, not per end-user account, so every process you run shares one budget. They're set per partner and not published; react to the headers.

> **Sandbox limits are significantly lower than production** and are not a reliable signal of production headroom. Alpaca explicitly says **not to load-test against sandbox** — mock the Alpaca calls instead and have the stub simulate latencies sampled from real production calls.

## 2. The retry loop (pseudocode)

```
MAX_ATTEMPTS = 10
INITIAL_DELAY_MS = 1000
MAX_DELAY_MS = 60000
backoff(n) = min(INITIAL_DELAY_MS * 2^(n-1), MAX_DELAY_MS) + random(0, 500)

for attempt in 1..MAX_ATTEMPTS:
    res = http(request)                      # with a sane timeout (see §5)
    limit, remaining, reset_at = parse_rate_headers(res.headers)
    if remaining < low_water(limit): log_warn("approaching rate limit", reset_at)

    if res.status == 429:
        # wait until the window resets, plus a small buffer
        wait = (reset_at - now()) if reset_at else backoff(attempt)
        sleep(max(0, wait) + 1000 + random(0, 500))
        continue

    if res.status in (500, 502, 503, 504) or network_error:
        sleep(backoff(attempt))
        continue

    return res                                # success or non-retryable 4xx
raise last_error
```

Key points:
- **On `429`, wait until `X-RateLimit-Reset` + a ~1s buffer**, then keep exponential backoff underneath — `Reset` says when the window rolls, not whether the herd behind you re-saturates it.
- **Exponential backoff** (`base * 2^(attempt-1)`) for network errors and 5xx, **capped** (the docs' example caps at 60s). With base 1s and 10 attempts the tail is minutes — fine for background jobs, too slow for user-facing calls (use fewer attempts there).
- **Jitter every wait.** It's part of the documented recommendation, not an extra: a correspondent-wide limit means all your workers are throttled together and would otherwise retry in lockstep.
- **Don't retry non-retryable 4xx** (`400`/`403`/`422`) — those won't fix themselves; surface them.

## 3. Bounded concurrency

Parallelism speeds bulk jobs but is the fastest way to hit limits. Use a **fixed worker pool**, not unbounded fan-out.

- **Size the pool from `X-RateLimit-Limit`**, not from a fixed number, and remember the limit is correspondent-level: every worker, cron job, and web process you run draws on the same budget. Tune down from observed `Remaining`; your own downstream store is often the tighter constraint.
- Cache per-entity reads **within a run** (e.g. an account's buying power, or a per-account transfer list) so you don't refetch the same thing across items in a batch.
- For per-item throttling, a small fixed sleep between calls (e.g. 100ms) is a crude-but-effective floor when you can't easily coordinate a pool.

## 4. Pagination loops

List endpoints page forward with a token — never assume one response is complete.

- **Activities** (`/v1/accounts/activities`): the response is a **bare JSON array** with no pagination header — pass the **`id` of the last activity in the page** back as `page_token` and stop when a page comes back short. `page_size` defaults to and maxes at 100 (no maximum when `date` is set — it returns everything); `direction` is `asc`/`desc`, default `desc`.
- **Market-data bars** (`/v2/stocks/bars`): page via `next_page_token` in the body → pass back as `page_token`. Remember `limit` counts across all symbols and results sort by symbol-then-time, so **a single page may contain only the first symbol(s)** — keep paging.
- Wrap each page fetch in the retry loop from §2.

```
token = null
loop:
    page = fetch(url + (token ? "&page_token="+token : ""))   # via retry loop
    accumulate(page.items)
    if body_token_endpoint:
        token = page.next_page_token
        if not token: break
    else:                              # activities: bare array, no token
        if len(page.items) < page_size: break
        token = page.items[-1].id
```

## 5. Timeouts & batch sizing

- **Always set an HTTP timeout** (15–30s is a reasonable starting point, not an Alpaca number). A hung connection without a timeout stalls a whole worker pool. (SSE streams are the exception — they're meant to stay open; see `alpaca-broker-sse-events`.)
- Use a **shared HTTP client / connection pool** rather than constructing one per request, so keep-alive and connection reuse work.
- **Detect silence on the market-data WebSocket and reconnect + resubscribe.** A slow client is disconnected, and the `407 slow client` error is "not guaranteed to arrive before you are disconnected" — so a dead socket can look identical to a quiet one (see `alpaca-broker-market-data`).
- When writing reconciliation results to your own store, **chunk bulk inserts** to stay under DB statement-size limits and keep transactions reasonable; pick the chunk size from your own database's behavior.

## 6. Resilience checklist for a bulk/cron job

- [ ] Rate-limit headers parsed every response; proactive warn near the limit.
- [ ] `429` → wait until `X-RateLimit-Reset` + buffer.
- [ ] Exponential backoff with jitter for 5xx/network; capped delay and capped attempts.
- [ ] Non-retryable 4xx surfaced, not retried.
- [ ] Bounded worker pool; per-run caching of repeated reads.
- [ ] Pagination loop until the token is empty.
- [ ] HTTP timeout on every call; shared client.
- [ ] Bulk DB writes chunked and idempotent (upsert) — see `alpaca-broker-reconciliation-idempotency`.
- [ ] Structured logging with a trace/correlation ID per item for debugging partial failures.

**Related skills:** safe re-runs of jobs → `alpaca-broker-reconciliation-idempotency`; the heal/poll jobs that use these patterns → `alpaca-broker-reconciliation-idempotency`; market-data pagination specifics → `alpaca-broker-market-data`.
