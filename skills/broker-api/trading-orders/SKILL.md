---
name: alpaca-broker-trading-orders
description: Place and manage orders on behalf of accounts via the Alpaca Broker API — order creation (qty vs notional, fractional shares, order types/TIF/classes), order status lifecycle, replace/cancel, positions, and trading-account buying power. Use when building trading, recurring-invest, or portfolio flows on Alpaca in any language.
---

# Alpaca Broker API — Trading on Behalf of Accounts

Place, modify, cancel, and track orders for an end-user account, and read positions & buying power. The defining feature of Broker API trading: **`account_id` is in the path** — you act *for* a user account, not your own.

> Read `alpaca-broker-integration` first. Broker API + HTTP Basic auth. (The standalone Trading API uses `/v2/orders` with no account in the path; everything else here transfers.)

## Reference
- Guides: `https://docs.alpaca.markets/docs/orders-at-alpaca`, `https://docs.alpaca.markets/docs/fractional-trading`
- API ref: `https://docs.alpaca.markets/reference/postorder`
- Live schema: `alpaca-docs` MCP → `get-endpoint` title `"Broker API"` path `/v1/trading/accounts/{account_id}/orders`

## 1. Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/trading/accounts/{id}/orders` | Create order |
| GET | `/v1/trading/accounts/{id}/orders` | List orders (filter by `status`, `symbols`, `after`…) |
| GET | `/v1/trading/accounts/{id}/orders/{order_id}` | Get order by ID |
| GET | `/v1/trading/accounts/{id}/orders:by_client_order_id?client_order_id=…` | Get by your client ID |
| PATCH | `/v1/trading/accounts/{id}/orders/{order_id}` | Replace (modify) order |
| DELETE | `/v1/trading/accounts/{id}/orders/{order_id}` | Cancel one order (204) |
| DELETE | `/v1/trading/accounts/{id}/orders` | Cancel all (207 Multi-Status) |
| POST | `/v1/trading/accounts/{id}/orders/estimation` | Cost-estimate an order |
| GET / DELETE | `/v1/trading/accounts/{id}/positions[/{symbol_or_asset_id}]` | List / close positions |
| GET | `/v1/trading/accounts/{id}/account` | Trading-account details (buying power etc.) |

## 2. Create-order request

Schema-required: `type` and `time_in_force`. Conditionally required: `symbol`, `side`, and exactly one of `qty`/`notional`.

```json
// notional market buy (dollar-based, fractional)
{ "symbol": "AAPL", "notional": "25.00", "side": "buy", "type": "market", "time_in_force": "day",
  "client_order_id": "your-own-uuid" }

// limit qty sell
{ "symbol": "AAPL", "qty": "3", "side": "sell", "type": "limit", "limit_price": "190.00", "time_in_force": "gtc" }
```

| Field | Values / notes |
|-------|----------------|
| `symbol` | required (except `mleg` multi-leg options) |
| `qty` | decimal **string**, up to 9 dp. Fractional only for `market`+`day` |
| `notional` | decimal **string**, up to 9 dp. **Mutually exclusive with `qty`** |
| `side` | `buy`, `sell` (plus advanced: `sell_short`, …) |
| `type` | `market`, `limit`, `stop`, `stop_limit`, `trailing_stop` |
| `time_in_force` | `day`, `gtc`, `opg`, `cls`, `ioc`, `fok` |
| `limit_price` / `stop_price` | required for limit/stop variants |
| `trail_price` / `trail_percent` | one required for `trailing_stop` |
| `extended_hours` | bool; only with `type=limit` and TIF `day`/`gtc` |
| `client_order_id` | ≤128 chars; **your idempotency key** (auto-generated if omitted) |
| `order_class` | `simple` (default), `bracket`, `oco`, `oto`, `mleg` |
| `take_profit` / `stop_loss` | `{limit_price}` / `{stop_price, limit_price?}` for bracket/oco/oto |
| `position_intent` | `buy_to_open`, `sell_to_close`, … |

**qty XOR notional (verbatim rule):** pass one or the other — supplying both → `400`. In the response, whichever you didn't use comes back `null`.

## 3. Fractional / notional rules

- **On by default** for all accounts (live + paper).
- Asset must have **`fractionable: true`** (check the Assets API — see `alpaca-broker-market-data`), else `requested asset is not fractionable`.
- **TIF must be `day`** for fractional/notional.
- **Notional** is limited to `market` and `limit` (day); only `limit` for extended hours. Fractional `qty` additionally allows `stop`/`stop_limit` per the guide.
- **No shorting fractional** — all fractional sells are marked long.
- Precision: up to **9 decimal places** for both `qty` and `notional`.

## 4. Order status lifecycle

`OrderStatus` (the order object's `status`): `new`, `partially_filled`, `filled`, `done_for_day`, `canceled`, `expired`, `replaced`, `pending_cancel`, `pending_replace`, `accepted`, `pending_new`, `accepted_for_bidding`, `stopped`, `rejected`, `suspended`, `calculated`.

> **Order `status` ≠ trade-event `event`.** The order object's `status` is the enum above. The **SSE trade-update stream** reports a *richer* `event` enum that adds operational events not present as a status — including `held` (multi-leg secondary legs awaiting trigger), `trade_bust`, `trade_correct`, `restated`, `order_cancel_rejected`, `order_replace_rejected`. So `held` exists as a trade *event* but never as an order *status*. See `alpaca-broker-sse-events`.

**Terminal:** `filled`, `canceled`, `expired`, `rejected` (and `replaced` for the original order). **Everything else is in-flight.**

**Early-state distinctions (these trip people up):**
- `accepted` — received by Alpaca, not yet routed to a venue (common outside market hours).
- `new` — received **and routed to exchanges**; the usual initial live state.
- `pending_new` — routed but not yet accepted for execution (rare).

So the typical opening sequence is `accepted → pending_new → new`, then fills. **Lesson:** treat `new`/`accepted`/`pending_new` as "exists but not done." Persist the order on submit, then update on fill/cancel/reject events — don't block the user waiting for a terminal state synchronously.

## 5. Positions & trading account

**`Position`** key fields: `symbol`, `asset_id`, `qty`, `qty_available` (free of open orders), `side` (`long`/`short`), `avg_entry_price`, `market_value`, `cost_basis`, `unrealized_pl`, `unrealized_plpc`, `current_price`, `change_today`.

**`TradeAccount`** key fields:
- `buying_power` (with margin `multiplier` 1–4), `cash`, `cash_withdrawable`, `equity`, `last_equity`.
- Blockers: `trading_blocked`, `account_blocked`, `transfers_blocked`, `trade_suspended_by_user`.
- `multiplier`, `regt_buying_power`, `non_marginable_buying_power`, `long_market_value`, `initial_margin`, `maintenance_margin`, `sma`.

**Lesson — check buying power before notional orders.** For a "spend $X" UX, read `buying_power`/`cash` first and reject/notify on insufficient funds, rather than letting Alpaca reject the order. (Cache it per account within a batch run to avoid re-fetching.)

> **PDT/day-trade fields are deprecated** (since 2026-04-27, sunset 2026-07-06) following FINRA's intraday-margin rule change: `daytrade_count`, `pattern_day_trader`, `daytrading_buying_power`, `bod_dtbp`, plus config `dtbp_check`/`pdt_check`. They still exist in the schema today but stop relying on them.

## 6. Documented gotchas

- **Wash-trade rejection (403):** if a user's two orders could self-cross (opposite sides, crossable prices), Alpaca rejects. Opposing market/stop pairs are always rejected; opposing limits rejected when buy-limit ≥ sell-limit. **Use `bracket`/`oco`/`trailing_stop` for simultaneous take-profit + stop-loss** — they're exempt.
- **Bracket constraints:** requires both `take_profit.limit_price` and `stop_loss.stop_price`; TP must be above SL for a buy; no extended hours; TIF `day`/`gtc`; child legs activate only after the entry fully fills; canceling one cancels the group.
- **Notional orders can't be replaced** — cancel and resubmit (IPO-class notional is the exception). Fractional `qty` can't be changed on replace ("full shares only").
- **Replace ≠ guaranteed:** a `200` from PATCH can still be rejected if the original fills first; watch the trade-updates stream. Can't replace while `accepted`/`pending_new`/`pending_cancel`/`pending_replace`.
- **Cancel semantics:** single cancel → `204`, or `422` if no longer cancelable; cancel-all → `207` per-order results; close-all positions → `207`. Close-single accepts mutually-exclusive `qty` or `percentage`.

## 7. Idempotency & recurring-invest lessons

- **Always set `client_order_id`** from your own transaction record. It's your dedup key and lets you look the order up (`orders:by_client_order_id`) if the create response is lost. Note it dedups *lookup*, not necessarily *replay* — combine it with a local "already-submitted?" guard.
- **Recurring/scheduled buys (lesson):** the robust pattern is — fetch pending invest instructions from your DB → check buying power → place a `notional` `market`/`day` order per instruction → record the returned order → mark the instruction done **only after** a successful create. On insufficient funds, cancel the instruction and notify, don't silently skip. Schedule the batch shortly **before** market open and respect the market clock (`alpaca-broker-market-data`).
- Track fills via the **trade events SSE stream**, not by polling each order — see `alpaca-broker-sse-events`.

**Related skills:** prices/assets/clock → `alpaca-broker-market-data`; fills in real time → `alpaca-broker-sse-events`; rate limits on bulk placement → `alpaca-broker-rate-limits-resilience`; money formatting → `alpaca-broker-money-precision`.
