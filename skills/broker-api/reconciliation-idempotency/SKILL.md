---
name: alpaca-broker-reconciliation-idempotency
description: Keep local state correct against the Alpaca Broker API — idempotency keys, ID-keyed upserts, event snapshotting and dedup, polling rails that have no events, windowed reconciliation/heal jobs, status state-machine mapping, and handling eventual consistency and corrections. Use when designing the data-correctness layer of any Alpaca integration in any language.
---

# Alpaca — Reconciliation & Idempotency

This is the skill that separates a demo from production. Alpaca is an **asynchronous, eventually-consistent** system: writes settle later, events can be missed or replayed, some rails emit no events at all, and "executed" can still be reversed. Your job is to make your local database a faithful, self-healing mirror of Alpaca's state.

> Read `alpaca-broker-integration`, `alpaca-broker-sse-events`, and the relevant domain skills first. This skill is the architecture that ties them together.

## The core principle

> **Treat Alpaca as the source of truth and your DB as a cache that must converge to it.** Every write is a request, not a fact. Every event is a hint, not a guarantee. Correctness comes from *idempotent* processing plus a *reconciliation* loop — never from assuming any single call or event succeeded exactly once.

## 1. Three layers of defense

```
Layer 1 — Idempotent writes      : never create a duplicate when you retry
Layer 2 — Idempotent event intake: never double-process a replayed/duplicate event
Layer 3 — Reconciliation sweep   : re-pull authoritative state and fix any drift
```

You need all three. Layer 1+2 keep you correct in the happy/retry case; Layer 3 catches everything that still slips through (downtime, bugs, missing events, corrections).

## 2. Layer 1 — Idempotent writes

Every money/order write must be safe to retry, because you can't tell a timeout apart from a success.

- **Orders:** set your own `client_order_id` (≤128 chars) derived from your transaction ID. On a lost response, look the order up via `orders:by_client_order_id` before retrying.
- **Journals:** send an `Idempotency-Key` header. Same key + same body returns the original journal; same key + different body → `422`. (See `alpaca-broker-journals`.)
- **Local-first ordering:** write your intent row (with a generated key) *before* the network call, so a crash mid-call leaves a record you can reconcile — never an orphaned Alpaca object you can't find.
- **Persist the returned Alpaca ID immediately** (`account_id`, `order_id`, `journal_id`, `transfer_id`). It is your only correlation key for events and reconciliation.

## 3. Layer 2 — Idempotent event intake

Events are **at-least-once**: replay cursors, reconnects, and corrections all cause the same event to arrive more than once.

- **Snapshot-first, keyed on the dedup id.** Insert the raw event with upsert / skip-on-duplicate so a duplicate becomes a no-op. Pick the key carefully: `event_id` (a ULID) is the **replay cursor**, and on the Activity SSE the **dedup key is `ref_id`**, the documented key for at-least-once redelivery on replay and for correction/bust linkage via `previous_id`. On the legacy status streams `event_id` fills both roles.
- **Key business records on the Alpaca ID**, not on a local autoincrement, with upsert semantics.
- **Guard transitions by current status.** Before acting, check the record isn't already terminal — so a duplicate "executed"/"filled" doesn't re-fire a payout or notification.
- **Serialize mutations per record.** Partitioning the consumer by `account_id` is the simplest default, since Alpaca guarantees per-account event ordering; a `SELECT … FOR UPDATE` row lock or an optimistic version column are the alternatives.
- **Advance the cursor only after success** (at-least-once, made safe by the above).

## 4. Layer 3 — Reconciliation / heal jobs

A scheduled job that re-pulls authoritative state from Alpaca and upserts it locally. This is what makes the system **self-healing**.

**Canonical windowed heal (lesson):**
1. Re-read **activities** from the Activity SSE (`GET /v2beta1/events/activities`) with `since`/`until` bounds. Bounded replay is a batch job, not a subscription: the stream ends with a `200` once it reaches `until`, and `since`/`until` filter on business time (`at`). (`GET /v1/accounts/activities` is marked fully replaced, but it is still the only source for activities booked before **2026-02-11**; use it for any window that reaches back past that date.)
2. Page through **journals** (`GET /v1/journals`) and **transfers** for the same window.
3. **Upsert** each into your tables keyed on the Alpaca ID (insert-or-update). Re-running is safe and converges.
4. Bound concurrency (a small worker pool) and respect rate limits (`alpaca-broker-rate-limits-resilience`).

Why a *window* and not just "since last run": it absorbs corrections, late settlements, and any events dropped during a deploy — without rescanning all history every night. Choose a window longer than your longest plausible outage.

## 5. Polling the rails that have no events

Not everything emits SSE. Where there's no event, you **must poll**.

- **Funding-wallet per-transfer status** (v1beta) is not pushed — poll `GET /v1beta/.../funding_wallet/transfers/{id}` on a schedule.
- Stagger pollers across the interval so the rails don't all fire together and spike API load.
- **Only poll records in a non-terminal state.** Filter your query to `status IN (pending, processing, …)`; once a record reaches a terminal status, drop it from the polling set. This bounds the work and prevents re-notifying.
- **Gotcha — no GET-by-id on classic wire transfers:** you must `GET /v1/accounts/{id}/transfers?direction=OUTGOING` (a *list*) and match the ID client-side; cache the list per account within a run.

**Lesson:** polling implies latency. Document the expected lag (e.g. "withdrawal status updates within ~1h") so product/support set the right expectations.

## 6. Status state-machine mapping

Alpaca exposes several status enums (account, order, journal, transfer, funding-wallet) — each with its own vocabulary. Don't scatter raw Alpaca strings through your app.

- **Define one explicit mapping table** per domain from Alpaca status → your internal status (e.g. transfer `COMPLETE` → `COMPLETED`; `REJECTED`/`CANCELED`/`RETURNED` → `CANCELLED`).
- **Casing and membership are not uniform.** Transfer statuses are UPPERCASE and include `RETURNED`; there is no `failed`. Journal statuses are lowercase. The REST `TransferStatus` enum and the funding-event enum aren't even the same set, so map the union of both.
- **Handle unknown statuses gracefully** — log and skip, never crash. Alpaca adds values over time.
- **Know which states are terminal** (they differ per enum) so you stop polling/processing them.

## 7. Eventual-consistency hazards to design for

- **`executed`/`COMPLETE` is not always final** — journals can be reversed by cashiering; transfers can be `RETURNED` after appearing done. Keep reconciling past the "happy" terminal state for a window.
- **Corrections create new IDs.** A journal `correct` cancels the original and issues a *new* journal ID carrying the real funds. Reconciliation keyed on event snapshots + Alpaca IDs handles this; logic that mutates the original record in place does not.
- **`200` means accepted, not settled.** Never confirm money moved to a user off the create response — confirm off the terminal event/poll.
- **Out-of-order & duplicate events** are normal (see `alpaca-broker-sse-events` §5). Idempotency absorbs them.

## 8. Anti-patterns (seen in the wild)

- ❌ Reconnecting an SSE stream **without** a since cursor (`since_id` on v2, `since_ulid` on v1) → silently drops every event during the gap. (Fix: persist + replay the cursor.)
- ❌ Treating an SSE stream as your *only* source → no backstop for missed events. (Fix: add the heal job.)
- ❌ Blind retry of a journal/order without an idempotency key → double money movement.
- ❌ Acting on `executed` as irreversible → broken books when a reversal/correction lands.
- ❌ Dedup keyed on a `confirmed` set instead of a `seen` set → judge/reject churn re-processes forever. Dedup on *everything seen*, key on the Alpaca/event ID.

## 9. Putting it together

```
WRITE:   local intent row (idempotency key) → Alpaca call → store Alpaca ID
LIVE:    SSE consumer (cursor-replay, snapshot-keyed dedup, status-guarded upsert)
POLL:    schedulers for rails with no events (non-terminal records only)
HEAL:    windowed re-pull of activities/journals/transfers → upsert
MAP:     Alpaca status → internal status, terminal-aware, unknown-tolerant
```

**Related skills:** event consumption mechanics → `alpaca-broker-sse-events`; idempotency keys per domain → `alpaca-broker-journals`, `alpaca-broker-trading-orders`; polling rails → `alpaca-broker-funding-transfers`; backoff & rate limits in heal jobs → `alpaca-broker-rate-limits-resilience`.
