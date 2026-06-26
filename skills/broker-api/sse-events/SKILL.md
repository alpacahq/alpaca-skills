---
name: alpaca-broker-sse-events
description: Consume Alpaca Broker API real-time event streams over Server-Sent Events (SSE) — account status, journal, transfer/funding, trade, and non-trade-activity events — reliably. Covers connection, auth, replay cursors (since/since_id), heartbeats, reconnection/backoff, ordering, and idempotent processing. Use when building an event consumer for Alpaca lifecycle events in any language.
---

# Alpaca Broker API — Real-Time Events (SSE)

Alpaca pushes brokerage lifecycle events over **Server-Sent Events**: a long-lived HTTP GET that streams `text/event-stream`. This is *not* the market-data WebSocket (`alpaca-broker-market-data`) — different transport, different auth, different reliability model.

> Read `alpaca-broker-integration` first. SSE uses the **Broker API host + HTTP Basic auth** (same credential as Broker REST).

## Reference
- Guide: `https://docs.alpaca.markets/docs/sse-events`
- Live: `alpaca-docs` MCP → `search` "SSE Events", then `fetch us/sse-events`

## 1. Why SSE (and why it's simpler than it looks)

SSE is plain HTTP. You don't need a special client: open a GET, keep the connection open, and read the body line-by-line. Each event is a `data:` line containing a JSON object. It is **replayable** — you can ask for events from a point in the past and seamlessly catch up to live, which makes it far better than naive polling for lifecycle state.

## 2. Event streams

| Stream | Path | Carries |
|--------|------|---------|
| Account status | `GET /v1/events/accounts/status` | Account-property changes: `status`/`crypto_status` (`SUBMITTED`→`ACTIVE`, `ACTION_REQUIRED`, `REJECTED`), plus `kyc_results`, `account_blocked`, `trading_blocked`, `cash_interest`, `options` |
| Journal status | `GET /v2/events/journals/status` | JNLC/JNLS lifecycle (`queued`→`executed`, `correct`…) |
| Funding/transfer status | `GET /v2/events/funding/status` | Unified: `Transfer`, `BankRelationship`, `WireBank`, `FundingWallet` entities (switch on `entity_type`) |
| Trade updates | `GET /v2/events/trades` | Order events in the `event` field: `new`, `fill`, `partial_fill`, `canceled`, `rejected`, `held`, `trade_bust`, `trade_correct`… (richer than order `status`) |
| Non-trade activities | `GET /v1/events/nta` | Dividends, interest, fees, splits, ACATs, cash disbursements. `entry_type` e.g. `JNLC`/`FEE`/`INT`/`DIVNRA`/`CSD`; `status` ∈ `executed`/`correct`/`canceled` |

> **Paths & versions are NOT uniform — verify each.** This is exactly the kind of cross-stream inconsistency Alpaca's docs under-communicate:
> - **`/v2`** streams (trades, journals/status, funding/status) use a **ULID** `event_id` directly; `/v1/events/trades` and `/v1/events/journals/status` are *legacy* (existing partners only — migrate to v2). `/v2/events/trades` was previously `/v2beta1`, now redirected.
> - **`/v1`** streams (accounts/status, nta) are **current, not deprecated** — there is no v2 yet. Each event carries **both** an integer `event_id` *and* a ULID `event_ulid`.
>
> Every event carries `at` (timestamp), `account_id`, and `status_from`/`status_to` (account/journal/funding) or `event`+`order` (trades).

## 3. Connection

```
GET /v2/events/journals/status?since_id=<last-ulid-you-saw> HTTP/1.1
Host: broker-api.alpaca.markets
Authorization: Basic <base64(key:secret)>
Accept: text/event-stream
```

Read the response stream and parse `data: {…}` frames as they arrive. In most languages an off-the-shelf EventSource/SSE client works — **just make sure it lets you set the `Authorization` header** on the initial request (the browser `EventSource` API famously does *not*; use a server-side SSE library instead).

## 4. Replay cursors — the feature that prevents data loss

Every stream supports point-in-time replay:

| Param | Meaning |
|-------|---------|
| `since` / `until` | Date or RFC3339 timestamps. **URL-encode `+`** in offsets as `%2B`. |
| `since_id` / `until_id` | ID cursors. On **v2** streams the ID *is* a ULID. On **v1** streams it's the **integer** `event_id`. |
| `since_ulid` / `until_ulid` | **v1 streams only** (accounts, nta) — ULID-based cursors, since v1 events carry both an int `event_id` and a `event_ulid`. |

Rules: `since` is required if `until` is set; `since_id` required if `until_id` set (same for `since_ulid`/`until_ulid`); you **can't mix** `since`, `since_id`, and `since_ulid`. **Without any since cursor, no history is returned** — you only get live pushes from now on. Reaching the `until` bound ends the stream with a `200`.

**This is the single most important reliability lesson:** persist the ID of the last event you *successfully processed*. On every (re)connect, pass it as your since cursor (`since_id` on v2; `since_ulid` or `since_id` on v1) so Alpaca replays anything you missed during the gap. A consumer that reconnects **without** a cursor silently drops every event that occurred while it was down.

## 5. Ordering caveat

Within a millisecond, ULIDs contain a random component, so two events in the same millisecond can sort either way. Alpaca's own guidance: **for reconciliation, restart the stream from a `since` a few minutes before your last event** and rely on idempotent processing to absorb the overlap. Don't assume strict total ordering — assume *approximate* ordering plus dedup.

## 6. Reliability patterns (hard-won)

SSE connections drop — networks, load balancers, deploys, and Alpaca-side resets all happen. A production consumer needs:

1. **Heartbeat / silence detection.** SSE has no application heartbeat by default. Track `lastMessageAt` on every frame; if the stream is silent past a threshold (e.g. 5 min), proactively tear down and reconnect — a dead socket often looks "open."
2. **Reconnect with exponential backoff + cap.** On error/close, reconnect after a delay that doubles up to a ceiling (e.g. start 1s, cap 60s). Reset the delay on a successful connect.
3. **A single-reconnect guard.** Use a flag so an error storm doesn't spawn many concurrent reconnect attempts racing each other.
4. **Always reconnect with `since_id`** = last processed event (see §4).
5. **Process idempotently** (see §7) — overlap from replay is expected, not exceptional.
6. **Don't let a side-effect failure kill the stream.** Wrap per-event processing in try/catch; log and continue. One bad event (or a downstream outage) must not stop you consuming the rest.

> Note: OpenAPI can't fully model SSE, so **generated API clients often hang** on these endpoints (waiting for a response that never ends). Use a real streaming HTTP/SSE client, not a codegen'd one.

## 7. Idempotent processing pipeline

The robust shape for each event:

```
parse → persist a raw event snapshot (keyed on event_id, skip-if-exists)
      → match the local record by Alpaca ID (account_id / journal_id / order_id / transfer_id)
      → update local state under a row lock / guarded by current status
      → fire side effects (notifications, downstream transfers)
      → advance the stored cursor to this event_id
```

- **Snapshot-first, keyed on `event_id`.** Insert the raw event with an upsert/skip-duplicate on `event_id`. A duplicate (from replay or an at-least-once redelivery) is then a no-op. This is your dedup boundary.
- **Lock the target row** (`SELECT … FOR UPDATE` or equivalent) when mutating a transfer/order so two events for the same record can't race.
- **Guard transitions by current status** — e.g. only act on a transfer that isn't already in a terminal state, so a late/duplicate "executed" doesn't re-trigger a payout.
- **Advance the cursor only after successful processing**, so a crash mid-event replays it rather than skipping it (at-least-once, which idempotency makes safe).

## 8. Per-stream notes

- **Account status:** drive onboarding UI and "enable trading" off `status_to == ACTIVE`. Reject sandbox/paper account IDs in live handlers.
- **Trade updates:** `new`/`accepted`/`pending_new` are pre-fill; update local order state on `fill`/`partial_fill`/`canceled`/`rejected`. Invalidate any cached portfolio/holdings on fills.
- **Journals:** remember `executed` isn't final and `correct` spawns a *new* journal ID (see `alpaca-broker-journals`). Idempotency + ID-keyed snapshots absorb both.
- **Funding/transfer:** unified stream across 4 entity types; switch on `entity_type`. Funding-wallet *per-transfer* status may still need polling (`alpaca-broker-funding-transfers`).
- **NTA:** dividends/fees/interest/corporate-actions — persist as activity snapshots; these feed balance/portfolio reconciliation.

## 9. SSE is necessary but not sufficient

Even a perfect consumer can miss events (extended downtime beyond retention, a bug, an un-handled type). **Always pair SSE with a periodic reconciliation/heal pass** that re-pulls authoritative state (activities, journals, transfers) from Alpaca and upserts it. SSE is for low latency; reconciliation is for correctness. See `alpaca-broker-reconciliation-idempotency`.

**Related skills:** correctness backstop → `alpaca-broker-reconciliation-idempotency`; dedup/idempotency mechanics → `alpaca-broker-reconciliation-idempotency`; backoff details → `alpaca-broker-rate-limits-resilience`; market-data streaming (WS, not SSE) → `alpaca-broker-market-data`.
