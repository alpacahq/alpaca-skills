---
name: alpaca-broker-journals
description: Move cash (JNLC) and securities (JNLS) BETWEEN accounts inside your own Alpaca omnibus via the Broker API — single, batch, and reverse-batch journals, the Idempotency-Key header, journal status lifecycle including corrections, and the firm/sweep-account pattern that powers instant funding and share rewards. Use for internal account-to-account movement in any language. For deposits/withdrawals to EXTERNAL banks, use funding-transfers instead.
---

# Alpaca Broker API — Journals

Journals move value **between two accounts within your own Alpaca omnibus** — typically between a pre-funded firm/sweep account and a user account. They are the engine behind "instant funding," cashback, and share rewards. They never touch the outside banking world (that's `alpaca-broker-funding-transfers`).

> Read `alpaca-broker-integration` first. Broker API + HTTP Basic auth.

## Reference
- Guide: `https://docs.alpaca.markets/docs/funding-via-journals`
- API ref: `https://docs.alpaca.markets/reference/createjournal`
- Live schema: `alpaca-docs` MCP → `get-endpoint` title `"Broker API"` path `/v1/journals`

## 1. Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/journals` | Single journal (JNLC cash or JNLS shares) |
| POST | `/v1/journals/batch` | One source → many destinations (JNLC only) |
| POST | `/v1/journals/reverse_batch` | Many sources → one destination (JNLC only) |
| GET | `/v1/journals` | List (filters: `after`, `before`, `status`, `entry_type`, `to_account`, `from_account`, `limit`) |
| GET | `/v1/journals/{journal_id}` | Retrieve one |
| DELETE | `/v1/journals/{journal_id}` | Cancel a **pending** journal (204) |
| GET | `/v2/events/journals/status` | **SSE** journal status stream (v1 is legacy) |

## 2. JNLC vs JNLS

`entry_type` is exactly `"JNLC"` or `"JNLS"`.

- **`JNLC` — cash.** Moves USD between accounts. Allowed **firm ↔ user, both directions**. Not customer-to-customer.
- **`JNLS` — securities.** Moves whole/fractional shares. Allowed **firm → user only**. Used for signup/referral share rewards.

```json
// JNLC (cash)
{ "entry_type": "JNLC", "from_account": "<firm-uuid>", "to_account": "<user-uuid>", "amount": "100.00" }

// JNLS (shares)
{ "entry_type": "JNLS", "from_account": "<firm-uuid>", "to_account": "<user-uuid>", "symbol": "AAPL", "qty": "0.5" }
```

| Field | JNLC | JNLS | Notes |
|-------|------|------|-------|
| `from_account` / `to_account` | required | required | account UUIDs |
| `amount` | **required** | — | decimal string |
| `symbol` / `qty` | — | **required** | qty is a string; fractional allowed |
| `currency` | optional | optional | defaults USD |
| `description` | optional | optional | ≤1024 chars; accepts sandbox fixtures |
| `transmitter_*` | optional (JNLC) | n/a | Travel Rule fields |

**Responses:** `200` journal · `403` amount/assets not available · `404` account not found · `422` idempotency-key reused with a different body.

## 3. Idempotency-Key header — USE IT

Pass an `Idempotency-Key` header (≤128 chars; a client-generated UUID is recommended) on journal creates.

- Same key + **identical** body → returns the original journal (no duplicate).
- Same key + **different** body → `422`.

**Lesson:** this is the correct way to make money movement retry-safe. Without it, a network timeout on `POST /v1/journals` leaves you unsure whether the cash moved — and a blind retry can double-fund. Generate the key deterministically from your own transaction ID and send it on every attempt.

## 4. Batch vs reverse-batch (JNLC only, all-or-nothing)

**Batch — one-to-many** (fan a sweep account out to many users):
```json
{ "entry_type": "JNLC", "from_account": "<firm-uuid>",
  "entries": [ { "to_account": "<u1>", "amount": "1000" }, { "to_account": "<u2>", "amount": "250" } ] }
```

**Reverse batch — many-to-one** (pull cash from many users back to the firm account):
```json
{ "entry_type": "JNLC", "to_account": "<firm-uuid>",
  "entries": [ { "from_account": "<u1>", "amount": "10" }, { "from_account": "<u2>", "amount": "100" } ] }
```

Every entry must validate or the **entire batch fails** (one bad account ID kills it). The response is an array of `BatchJournalResponse` (the Journal object + an `error_message` per entry that failed). `Idempotency-Key` is supported with the same semantics.

## 5. Status lifecycle

`JournalStatus`: `queued`, `sent_to_clearing`, `pending`, `executed`, `rejected`, `canceled`, `refused`, `deleted`, `correct`.

**Happy path:** `queued → sent_to_clearing → executed`.

| Status | Meaning | Terminal |
|--------|---------|----------|
| `queued` | In queue | no |
| `sent_to_clearing` | Submitted to books-and-records | no |
| `pending` | Needs Alpaca ops approval (e.g. hit a JNLC daily limit) | no |
| `executed` | Balances updated — **but NOT final**, can still be reversed by cashiering | no (not final) |
| `rejected` | Manually rejected | no |
| `refused` | Failed preliminary checks; never hit the ledger (e.g. a fast replay failing the balance check) | no |
| `canceled` | Canceled via API/ops | **FINAL** |
| `deleted` | Removed from ledger | **FINAL** |
| `correct` | A prior executed journal was cancelled and re-created with a corrected amount | **FINAL** |

**Two critical lessons:**
1. **`executed` ≠ final.** Don't treat `executed` as irreversible — Alpaca cashiering can reverse a journal that wasn't permitted. Reconcile against later events.
2. **`correct` creates a NEW journal ID.** A correction cancels the original and issues a *new* journal with the corrected amount — it is **not** an in-place edit. If you reconcile by journal ID, the original ID transitions to `correct`/cancelled while a *different* ID carries the real funds. Handle both. (This is why event consumers must be idempotent and ID-keyed — see `alpaca-broker-reconciliation-idempotency`.)

## 6. SSE journal events

`GET /v2/events/journals/status` pushes `JournalStatusEventV2`: `event_id` (ULID, sortable), `journal_id`, `entry_type`, `status_from`, `status_to`, `description`, `idempotency_key`, `idempotency_key_type` (`single`|`batch`), `batch_error_message`. Replay rules: `since` required if `until` set; `since_id` required if `until_id` set; can't mix `since` with `since_id`. Without a `since`/`since_id`, no history is returned. See `alpaca-broker-sse-events`.

## 7. Constraints & gotchas

- **Eligibility:** the cash-pooling/journals use case requires Alpaca review and possibly a local license — check with counsel.
- **JNLS account states:** `to_account` must be `ACTIVE`; `from_account` must be `ACTIVE` or `CLOSE`.
- **Sufficient funds:** JNLC create → `403` if the amount isn't available; reverse-batch `403` = insufficient balance/assets.
- **Daily limits push to `pending`** (manual ops approval).
- **`GET /v1/journals` returns `422` if the result set exceeds 100,000 records** — always filter with `after`/`before`/`limit`.
- **Delete is pending-only:** `DELETE` succeeds (204) only when `pending`; an executed journal → `422`. **To reverse an executed journal, create a mirror journal in the opposite direction**, don't try to delete it.
- **Travel Rule:** include transmitter info on money-moving journals (required on all incoming deposits regardless of amount).
- **Sandbox fixtures:** put fixtures in `description` (e.g. `/fixtures/status=rejected/fixtures/`) to simulate `rejected`/`pending` outcomes for testing.

## 8. The sweep-account funding pattern (why journals exist)

The canonical Broker API funding architecture:

```
Bulk external wire ──> FIRM / SWEEP account (pre-funded) ──JNLC──> user accounts (instant)
user account ──JNLC──> FIRM account ──external wire/ACH──> outside world (withdrawal)
```

You collect money your own way, hold it in a firm account, and **journal it to users instantly** rather than running a per-user external transfer. Withdrawals reverse the flow. This is what makes "instant deposit" UX possible on top of slow banking rails.

**Related skills:** external money in/out → `alpaca-broker-funding-transfers`; retry-safety & corrections → `alpaca-broker-reconciliation-idempotency`; decimal handling → `alpaca-broker-money-precision`; events → `alpaca-broker-sse-events`.
