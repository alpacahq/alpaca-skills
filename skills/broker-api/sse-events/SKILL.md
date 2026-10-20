---
name: alpaca-broker-sse-events
description: Consume Alpaca Broker API real-time event streams over Server-Sent Events (SSE) — account status, journal, transfer/funding, trade, and non-trade-activity events — reliably. Covers connection, auth, replay cursors (since / since_id / since_ulid), heartbeat and comment lines, reconnection/backoff, ordering, and idempotent processing. Use when building an event consumer for Alpaca lifecycle events in any language.
---

# Alpaca Broker API — Real-Time Events (SSE)

Alpaca pushes brokerage lifecycle events over **Server-Sent Events**: a long-lived HTTP GET that streams `text/event-stream`. This is *not* the market-data WebSocket (`alpaca-broker-market-data`) — different transport, different auth, different reliability model.

> Read `alpaca-broker-integration` first for base URLs and auth (client-credentials Bearer token; legacy Basic still works).

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
| Activities | `GET /v2beta1/events/activities` | Every financial activity in one stream: fills, corporate actions, fees, journals, transfers. `activity_type` (`TRD` = trade fill) + `activity_subtype` + a `details` object; ULID `event_id`, UUID `ref_id` |
| Non-trade activities (legacy) | `GET /v1/events/nta` | Dividends, interest, fees, splits, ACATs, cash disbursements. `entry_type` e.g. `JNLC`/`FEE`/`INT`/`DIVNRA`/`CSD`; `status` ∈ `executed`/`correct`/`canceled` |

> **Paths & versions are NOT uniform — verify each.** This is exactly the kind of cross-stream inconsistency Alpaca's docs under-communicate:
> - **The Activity SSE fully replaces `/v1/events/nta` and `GET /v1/accounts/activities`** for activities booked after **2026-02-11**; older history still needs the REST endpoint. New partners should not use the legacy endpoints. It does **not** replace `/v2/events/trades`: fills, corrections and busts appear on both, but non-fill lifecycle events (`accepted`, `canceled`, `expired`, `replaced`) are not activities and never appear on it.
> - **`/v1/events/trades` is gone** (fully deprecated, no longer available). `/v1/events/journals/status` is legacy — migrate to `/v2`.
> - **`/v1`** events carry an integer `event_id` *and* a ULID `event_ulid`; **`/v2`/`/v2beta1`** carry a ULID `event_id`. §4 says which cursor to pass.
>
> Field shapes differ per stream — there is no universal envelope. Check each schema.

## 3. Connection

```
GET /v2/events/journals/status?since_id=<last-ulid-you-saw> HTTP/1.1
Host: broker-api.alpaca.markets
Authorization: Bearer <access-token>
Accept: text/event-stream
```

`Authorization: Basic <base64(key:secret)>` also works. Nothing documents whether an open stream survives token expiry, so treat a mid-stream `401` as just another drop and reconnect with your cursor.

Read the response stream and parse `data: {…}` frames as they arrive. In most languages an off-the-shelf EventSource/SSE client works — **just make sure it lets you set the `Authorization` header** on the initial request (the browser `EventSource` API famously does *not*; use a server-side SSE library instead).

## 4. Replay cursors — the feature that prevents data loss

Every stream supports point-in-time replay:

| Param | Meaning |
|-------|---------|
| `since` / `until` | RFC3339 or `YYYY-MM-DD` timestamps (date-only on some `/v1` streams). **URL-encode `+`** in offsets as `%2B`. |
| `since_id` / `until_id` | **v2 / v2beta1 streams — ULID values.** On `/v1/events/*` these are the *legacy integer* cursors: available only to select broker partners and sunset **2027-02-15**. Don't build on them. |
| `since_ulid` / `until_ulid` | **v1 streams** (accounts/status, nta, and the legacy `/v1` journals stream) — the ULID cursors, available to all partners. Use these on v1; they don't exist on v2. |

Rules: `since` is required if `until` is set; `since_id` required if `until_id` set (same for `since_ulid`/`until_ulid`); you **can't mix** `since`, `since_id`, and `since_ulid`. On `/v2beta1/events/activities` the dependency flips: **`since` requires `until`**, and only `since_id` can be left open-ended for live tailing. **Without any since cursor, no history is returned** — you only get live pushes from now on. Reaching the `until` bound ends the stream with a `200`.

**This is the single most important reliability lesson:** persist the ID of the last event you *successfully processed*. On every (re)connect, pass it as your since cursor — **`since_id` on v2/v2beta1, `since_ulid` on v1** — so Alpaca replays anything you missed during the gap. A consumer that reconnects **without** a cursor silently drops every event that occurred while it was down.

## 5. Ordering caveat

Within a millisecond, ULIDs contain a random component, so two events in the same millisecond can sort either way. Alpaca's own guidance: **for reconciliation, restart the stream from a `since` a few minutes before your last event** and rely on idempotent processing to absorb the overlap. Alpaca guarantees ordering **per account**; across accounts it guarantees nothing. So assume *approximate* global ordering plus dedup — and exploit the per-account guarantee (see §7).

## 6. Reliability patterns (hard-won)

SSE connections drop — networks, load balancers, deploys, and Alpaca-side resets all happen. A production consumer needs:

1. **Parse comment lines — never discard them.** Any `:`-prefixed line is an SSE comment, and Alpaca carries three meanings there: `:heartbeat` (alive, no action); `: you are reading too slowly, dropped N messages` (**silent data loss** — treat it as a gap and re-replay from your cursor); `: internal server error` (server is closing — reconnect; v2/v2beta1 streams only). A consumer that filters `:` lines loses data without noticing.
2. **Silence detection.** Track `lastMessageAt` on every frame, heartbeats included; if the stream goes quiet for a small multiple of the heartbeat cadence you observe, tear down and reconnect — a dead socket often looks "open." The cadence isn't documented, so measure it rather than hardcoding a timeout.
3. **No blocking I/O in the reader loop.** Alpaca's explicit guidance: read into a queue, process on a worker. A synchronous DB write per event is what earns you the `dropped N messages` comment.
4. **Reconnect with exponential backoff + cap.** On error/close, reconnect after a delay that doubles up to a ceiling (e.g. start 1s, cap 60s). Reset the delay on a successful connect.
5. **A single-reconnect guard.** Use a flag so an error storm doesn't spawn many concurrent reconnect attempts racing each other.
6. **Always reconnect with your cursor** = last processed event (`since_id` on v2, `since_ulid` on v1; see §4).
7. **Process idempotently** (see §7) — overlap from replay is expected, not exceptional.
8. **Don't let a side-effect failure kill the stream.** Wrap per-event processing in try/catch; log and continue. One bad event (or a downstream outage) must not stop you consuming the rest.

> Note: OpenAPI can't fully model SSE, so **generated API clients often hang** on these endpoints (waiting for a response that never ends). Use a real streaming HTTP/SSE client, not a codegen'd one.

## 7. Idempotent processing pipeline

The robust shape for each event, run on a worker rather than in the reader loop (§6):

```
parse → persist a raw event snapshot (keyed on the dedup id, skip-if-exists)
      → match the local record by Alpaca ID (account_id / journal_id / order_id / transfer_id)
      → update local state guarded by current status, serialized per record
      → fire side effects (notifications, downstream transfers)
      → advance the stored cursor to this event_id
```

- **Keep the two ids apart.** `event_id` is the *replay cursor*; the *dedup key* is the business id. On the Activity SSE that's `ref_id` (execution id for trades, transaction id otherwise): replay redelivers events at-least-once, and corrections/busts link back through `previous_id`, so `ref_id` is the documented dedup key. Backfilled activities arrive late, at the end of the `event_id` sequence, with their original `at`. On the legacy status streams `event_id` is both.
- **Serialize mutations per record** so two events for one transfer/order can't race. Partitioning workers by `account_id` is the simplest default and is what the per-account ordering guarantee (§5) buys you; a `SELECT … FOR UPDATE` row lock or an optimistic version column are alternatives.
- **Guard transitions by current status** — e.g. only act on a transfer that isn't already in a terminal state, so a late/duplicate "executed" doesn't re-trigger a payout.
- **Advance the cursor only after successful processing**, so a crash mid-event replays it rather than skipping it (at-least-once, which idempotency makes safe).

## 8. Per-stream notes

- **Account status:** drive onboarding UI and "enable trading" off `status_to == ACTIVE`.
- **Trade updates:** `new`/`accepted`/`pending_new` are pre-fill; update local order state on `fill`/`partial_fill`/`canceled`/`rejected`. Invalidate any cached portfolio/holdings on fills.
- **Journals:** remember `executed` isn't final and `correct` spawns a *new* journal ID (see `alpaca-broker-journals`). Idempotency + ID-keyed snapshots absorb both.
- **Funding/transfer:** unified stream across 4 entity types; switch on `entity_type`. Transfer statuses are **UPPERCASE** (`QUEUED`, `APPROVAL_PENDING`, `APPROVED`, `SENT_TO_CLEARING`, `COMPLETE`, `REJECTED`, `CANCELED`, `EXPIRED`, `RETURNED`), and the funding-event list differs from the REST `TransferStatus` enum — which adds `PENDING` and drops `EXPIRED` — so accept the union. Funding-wallet *per-transfer* status may still need polling (`alpaca-broker-funding-transfers`).
- **Activities / NTA:** dividends/fees/interest/corporate-actions and fills — persist as activity snapshots keyed on `ref_id`; these feed balance/portfolio reconciliation. `previous_id` on an activity carries the corrected activity's `ref_id`.

## 9. SSE is necessary but not sufficient

Even a perfect consumer can miss events (extended downtime beyond retention, a bug, an un-handled type). **Always pair SSE with a periodic reconciliation/heal pass** that re-pulls authoritative state (activities, journals, transfers) from Alpaca and upserts it. SSE is for low latency; reconciliation is for correctness. See `alpaca-broker-reconciliation-idempotency`.

**Related skills:** correctness backstop → `alpaca-broker-reconciliation-idempotency`; dedup/idempotency mechanics → `alpaca-broker-reconciliation-idempotency`; backoff details → `alpaca-broker-rate-limits-resilience`; market-data streaming (WS, not SSE) → `alpaca-broker-market-data`.
