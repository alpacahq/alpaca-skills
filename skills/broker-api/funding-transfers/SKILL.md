---
name: alpaca-broker-funding-transfers
description: Move money between an Alpaca brokerage account and the EXTERNAL banking world via the Broker API — ACH relationships, wire recipient banks, classic transfers (deposits/withdrawals), the v1beta funding wallet (international/instant), transfer status lifecycles, and fees. Use when building deposit/withdrawal flows or connecting external bank accounts on Alpaca in any language. For moving cash/shares BETWEEN accounts inside your own omnibus, use journals instead.
---

# Alpaca Broker API — Funding & Transfers

Getting cash into and out of end-user accounts. There are **three rails**, and the model splits cleanly into *bank links* (persistent) and *transfers* (the actual money movement).

> Read `alpaca-broker-integration` first. Broker API + HTTP Basic auth. For moving cash *between* accounts in your omnibus (vs. to/from the outside world), see `alpaca-broker-journals` — that's a different mechanism.

## Reference
- Guide: `https://docs.alpaca.markets/docs/funding-accounts`
- API ref: `https://docs.alpaca.markets/reference/createtransferforaccount`
- Live schema: `alpaca-docs` MCP → `get-endpoint` title `"Broker API"` path `/v1/accounts/{account_id}/transfers`

## 1. The funding model

```
External bank ──(relationship: a persistent link)──┐
                                                    ├──> Transfer (the money movement) ──> Account cash
ACH relationship  (rail A: ACH, US domestic)        │
Bank relationship (rail B: wire, domestic + intl)   │
Funding wallet    (rail C: v1beta, multi-currency)  ┘
```

- A **relationship** links an external bank. It moves no money and has its own status; for wires it must be `APPROVED` before a transfer can progress.
- A **transfer** references a relationship by ID and moves the money. One relationship backs many transfers.

| Rail | `transfer_type` | Directions | Relationship | Notes |
|------|-----------------|-----------|--------------|-------|
| **ACH** | `ach` | `INCOMING` + `OUTGOING` | ACH relationship (`relationship_id`) | US domestic; set up via Plaid `processor_token` (recommended) |
| **Wire** | `wire` | `OUTGOING` only | Bank relationship (`bank_id`) | Domestic + international (SWIFT). Incoming wires are pushed by the sending bank and booked automatically |
| **Funding wallet** | (separate `/v1beta` API) | `incoming` / `outgoing` (lowercase) | Funding-wallet recipient bank | Multi-currency, `swift_wire`/`local_rails` |

## 2. Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST/GET/DELETE | `/v1/accounts/{id}/ach_relationships[/{rel_id}]` | Manage ACH bank links |
| POST/GET/DELETE | `/v1/accounts/{id}/recipient_banks[/{bank_id}]` | Manage wire recipient banks |
| POST | `/v1/accounts/{id}/transfers` | Create transfer (ACH deposit/withdraw, or wire withdraw) |
| GET | `/v1/accounts/{id}/transfers` | List transfers |
| DELETE | `/v1/accounts/{id}/transfers/{transfer_id}` | Request cancel |
| POST/GET | `/v1beta/accounts/{id}/funding_wallet` | Create / get funding wallet |
| POST/GET/DELETE | `/v1beta/accounts/{id}/funding_wallet/recipient_bank` | Funding-wallet recipient bank |
| POST | `/v1beta/accounts/{id}/funding_wallet/withdrawal` | Funding-wallet withdrawal |
| GET | `/v1beta/accounts/{id}/funding_wallet/transfers[/{transfer_id}]` | List / get wallet transfers |
| GET | `/v2/events/funding/status` | **SSE** — unified funding status stream (see §6) |

> The current wire-bank endpoint is **`/recipient_banks`** (schema `Bank`/`CreateBankRequest`). The older `/banks` name is a legacy alias.

## 3. Create-transfer request (`POST /v1/accounts/{id}/transfers`)

Required for all: `transfer_type`, `amount` (decimal **string**, > 0), `direction`.

```json
// ACH deposit
{ "transfer_type": "ach", "relationship_id": "<uuid>", "amount": "100.00", "direction": "INCOMING" }

// Wire withdrawal
{ "transfer_type": "wire", "bank_id": "<uuid>", "amount": "500.00", "direction": "OUTGOING",
  "fee_payment_method": "user", "additional_information": "..." }
```

- `relationship_id` required iff `ach`; `bank_id` required iff `wire` (and must be the *other* one's empty).
- `fee_payment_method` (wire): `user` (fee deducted from `amount`; warn the user in UI) or `invoice` (firm billed monthly). Only **outgoing** wire fees auto-process.
- `additional_information` is wire-only — sending it on a non-wire request returns `422`.
- The `Transfer` response adds `id`, `status`, `fee`, `requested_amount` (original ask), `reason`, timestamps.

## 4. Wire recipient bank (`POST /v1/accounts/{id}/recipient_banks`)

Required: `name`, `bank_code`, `bank_code_type`, `account_number`.

- `bank_code_type`: `ABA` (9-digit routing, domestic) or `BIC` (SWIFT, international).
- When `BIC`: `country`, `city`, `state_province`, `postal_code`, `street_address` become required.
- `extra_fields` carries intermediary/correspondent BICs (`intermediary_bank1_bic`…). **Omitting them on international wires can cause auto-selection, delays, or extra fees** — gather them up front for cross-border.
- A new bank starts `QUEUED`; it must reach `APPROVED` before a wire transfer against it progresses.

## 5. Transfer status state machines

**Classic transfers (`TransferStatus`):**
`QUEUED → APPROVAL_PENDING → PENDING → SENT_TO_CLEARING → (APPROVED) → COMPLETE`, with `REJECTED` / `CANCELED` / `RETURNED` as failure exits.

| Terminal | Meaning |
|----------|---------|
| `COMPLETE` | Settled |
| `REJECTED` | Rejected |
| `CANCELED` | Client-initiated cancel |
| `RETURNED` | Bank issued an ACH return |

(The SSE `Transfer` entity also reports `EXPIRED`, which is effectively terminal.)

**Funding-wallet transfers (`FundingWalletTransferStatus`):** `PENDING`, `EXECUTED`, `COMPLETE`, `CANCELED`, `FAILED` (last three terminal). Note lowercase `incoming`/`outgoing` directions here — different casing from classic transfers.

## 6. Events vs polling — the key reliability lesson

**Classic transfers HAVE an SSE stream:** `GET /v2/events/funding/status`. It is unified across four `entity_type` values — `Transfer`, `BankRelationship`, `WireBank`, `FundingWallet` — and is **replayable** via `since`/`until` (timestamps) or `since_id`/`until_id` (ULIDs). Use it instead of polling for classic ACH/wire status.

**Funding-wallet *per-transfer* status appears NOT to be pushed** — only wallet-level status (`active`/`pending`) is in the stream. Individual wallet transfer status (`PENDING→EXECUTED→COMPLETE`) must be **polled** via `GET /v1beta/.../funding_wallet/transfers/{id}`.

**Lesson (hard-won):** rails differ in event coverage. Decide per rail whether you consume SSE or poll, and build a **status-reconciliation poller** for anything not covered by events (and as a safety net even for those that are — SSE can drop). Map each Alpaca status to your own internal status with an explicit lookup table, and only poll transfers still in a **non-terminal** state. See `alpaca-broker-reconciliation-idempotency`.

> Legacy caveat: the older `us/sse-events` "Transfer Events" payload uses an **integer** `event_id` and lowercase statuses; the modern `/v2/events/funding/status` uses ULIDs. Migrate to v2.

## 7. Documented gotchas

- **Wire fees (since 2022-06-01):** outgoing domestic + international wires are charged. Reflect `requested_amount` vs `amount`+`fee` in your UI.
- **Incoming wires need an FFC (For Further Credit) instruction** to auto-book; otherwise they're handled manually.
- **Travel Rule:** Alpaca requires transmitter/originator info on **all incoming deposits regardless of amount** (below the usual FinCEN $3,000 threshold). Pass it at settlement creation; retained ≥5 years.
- **ACH uses Plaid:** pass the bank via `processor_token`. There's an `instant` flag on the relationship. Account types limited to `CHECKING`/`SAVINGS`.
- **`timing: immediate` is deprecated** and silently ignored (sunset 2026-08-26) — stop sending it.
- **Permission errors:** `403` if the account's `depositable_status`/`withdrawable_status` isn't allowed; `422` for incoming-wire attempts, missing/mismatched relationship vs bank IDs, or amounts under the (undocumented) minimums.
- **Sandbox wire behavior:** simulated end-to-end but **asynchronous** and auto-completes **on weekdays only** — weekend submissions don't progress until Monday. (ACH in sandbox settles instantly.)

## 8. The omnibus / sweep-account pattern (architecture lesson)

Many production brokers don't fund each user account by a separate external transfer. Instead:

1. Users pay you through *your* payment processor (or you receive a bulk wire into a **firm/sweep account** held at Alpaca).
2. You then **journal** cash from the firm account to the user's account instantly (`JNLC`) — no external ACH/wire per user. See `alpaca-broker-journals`.
3. Withdrawals reverse it: journal from user → firm account, then send one external transfer out.

This decouples your funding UX from Alpaca's transfer rails and enables "instant" deposits. It requires Alpaca review (and possibly a local money-transmitter license) — confirm with counsel. The classic transfer endpoints in this skill then handle only the *firm-account-to-outside-world* leg.

**Related skills:** internal cash movement → `alpaca-broker-journals`; missed-status recovery → `alpaca-broker-reconciliation-idempotency`; money formatting → `alpaca-broker-money-precision`; live status → `alpaca-broker-sse-events`.
