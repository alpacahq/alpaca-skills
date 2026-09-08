---
name: alpaca-broker-funding-transfers
description: Move money between an Alpaca brokerage account and the EXTERNAL banking world via the Broker API — ACH relationships, wire recipient banks, classic transfers (deposits/withdrawals), the v1beta funding wallet (international/instant), transfer status lifecycles, and fees. Use when building deposit/withdrawal flows or connecting external bank accounts on Alpaca in any language. For moving cash/shares BETWEEN accounts inside your own omnibus, use journals instead.
---

# Alpaca Broker API — Funding & Transfers

Getting cash into and out of end-user accounts. There are **three external rails** plus Instant Funding, and for the external rails the model splits cleanly into *bank links* (persistent) and *transfers* (the actual money movement).

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
| **Instant Funding** | (separate `/v1/instant_funding` API) | credit only | none — you collect the payment yourself | Extends buying power immediately, settled in bulk by wire on T+1. See §8 |

## 2. Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST/GET/DELETE | `/v1/accounts/{id}/ach_relationships[/{rel_id}]` | Manage ACH bank links |
| POST/GET/DELETE | `/v1/accounts/{id}/recipient_banks[/{bank_id}]` | Manage wire recipient banks |
| POST | `/v1/accounts/{id}/transfers` | Create transfer (ACH deposit/withdraw, or wire withdraw) |
| GET | `/v1/accounts/{id}/transfers` | List transfers |
| DELETE | `/v1/accounts/{id}/transfers/{transfer_id}` | Request cancel |
| POST/GET | `/v1beta/accounts/{id}/funding_wallet` | Create / get funding wallet |
| GET | `/v1beta/accounts/{id}/funding_wallet/funding_details` | Deposit instructions for the wallet |
| POST/GET/DELETE | `/v1beta/accounts/{id}/funding_wallet/recipient_bank` | Funding-wallet recipient bank |
| POST | `/v1beta/accounts/{id}/funding_wallet/withdrawal` | Funding-wallet withdrawal |
| GET | `/v1beta/accounts/{id}/funding_wallet/transfers[/{transfer_id}]` | List / get wallet transfers |
| POST/GET/DELETE | `/v1/instant_funding[/{instant_funding_id}]` | Create / get / reverse an instant funding transfer |
| GET | `/v1/instant_funding/limits` | Correspondent-level limits (`/limits/accounts` for per-account) |
| POST | `/v1/instant_funding/settlements` | Trigger settlement of created transfers |
| GET | `/v2/events/funding/status` | **SSE** — unified funding status stream (see §6) |

> The current wire-bank endpoint is **`/recipient_banks`** (schema `Bank`/`CreateBankRequest`). The older `/banks` name is a legacy alias.

**Wallet deposit flow:** create the wallet → `GET .../funding_wallet/funding_details` for the instructions to hand the customer → customer pushes funds (in sandbox, `POST /v1beta/demo/banking/funding`) → poll `GET .../funding_wallet/transfers`.

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

**Funding-wallet transfers:** `PENDING` → `EXECUTED` → `COMPLETE`, with `REJECTED` (bank rejected, usually bad input) and `FAILED` (bank error) as the other exits. Wallet transfers **cannot be canceled**; the terminal set is `COMPLETE` / `REJECTED` / `FAILED`. The OpenAPI `FundingWalletTransferStatus` enum still lists `CANCELED` and omits `REJECTED` — trust the guide and treat the union as terminal. Note lowercase `incoming`/`outgoing` directions here — different casing from classic transfers.

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
- **Permission errors:** `403` when the account isn't permitted to deposit or withdraw. The message names the failing permission (`depositable_status` / `withdrawable_status`); neither exists as a field on the account object, so there is nothing to pre-check — handle the 403 and surface its message. `422` for incoming-wire attempts, missing/mismatched relationship vs bank IDs, or amounts under the (undocumented) minimums.
- **Sandbox wire behavior:** simulated end-to-end but **asynchronous** and auto-completes **on weekdays only** — weekend submissions don't progress until Monday. (ACH in sandbox settles instantly.)

## 8. Instant availability: two supported models

Alpaca documents two ways to let a user trade before their cash lands, with different settlement obligations.

**Cash pooling (omnibus + journals)** — the docs call this the most common use case: bulk-wire into your pre-funded firm account, then `JNLC` to the user the moment you receive their payment; reverse for withdrawals. You pre-fund, so you owe Alpaca nothing per transfer. Requires Alpaca review and possibly a local money-transmitter license. See `alpaca-broker-journals`.

**Instant Funding** — `POST /v1/instant_funding` extends buying power at the user account without pre-funding, so Alpaca is extending you credit and you settle later. Per-account limit defaults to USD 1,000 (raiseable on request); correspondent headroom is `GET /v1/instant_funding/limits`, per-account headroom is `GET /v1/instant_funding/limits/accounts?account_numbers=…`.

Settlement is your obligation and it is tight. Transfers batch in a 24-hour window ending 8 PM ET, you wire one bulk payment to your `SI` firm account, then call `POST /v1/instant_funding/settlements` (carrying the Travel Rule `originator_*` fields) **before 1 PM ET on T+1**. Late settlement accrues penalty interest at FED UB + 8%, invoiced monthly. Unreconciled transfers auto-cancel at **8 PM ET on T+1**, which drops the customer account into a debit balance if they already spent the credit. Full flow: `https://docs.alpaca.markets/us/docs/instant-funding`.

**Related skills:** internal cash movement → `alpaca-broker-journals`; missed-status recovery → `alpaca-broker-reconciliation-idempotency`; money formatting → `alpaca-broker-money-precision`; live status → `alpaca-broker-sse-events`.
