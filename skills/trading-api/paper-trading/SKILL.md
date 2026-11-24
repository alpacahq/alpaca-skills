---
name: alpaca-trading-paper-trading
description: >
  Preview, submit, inspect, and manage Alpaca paper-trading orders across US
  equities, options, and crypto. Use this skill when you want your AI agent to
  take a strategy signal — from a backtest, manual idea, or automated system —
  and execute it safely in your Alpaca paper-trading environment. This generic
  version works with any Alpaca SDK, REST API call, or agent tool that can
  reach the Trading API.
---

# Alpaca Paper Trading

Use this skill when you want your AI agent to preview, submit, inspect, and manage paper-trading orders using Alpaca's Trading API.

This skill is written for you, a Trading API user working with your own Alpaca paper-trading account, credentials, and local workspace. Your agent should make assumptions visible, protect secrets, and confirm order details before submission.

This is the generic (implementation-agnostic) version of the paper-trading skill. It describes the workflow, safety gates, and output contract without binding to any specific execution tool. You can use the Alpaca Python SDK (`alpaca-py`), the REST API directly, JavaScript/TypeScript, Go, C#, or any tool that speaks to the Trading API. CLI-specific and MCP-specific companion skills exist for users who prefer those execution paths — see §10 for links.

---

## 0 - How your AI agent should use this skill

1. **Start with your job.** Identify what the signal is — a backtest output, a manual trade idea, a scheduled trigger, or an automated system event. Your agent reads any associated context (backtest run folder, strategy description, alert payload) to understand the intent.

2. **Reiterate the strategy logic.** Your agent restates the strategy interpretation in plain language — entry/exit conditions, indicator parameters, position sizing, and any assumptions — and confirms with you that the interpretation is correct before proceeding.

3. **Gather and confirm ALL detailed configurations before execution.** Your agent collects every order parameter explicitly:
   - Timing of execution (immediate, scheduled, conditional)
   - Asset class (US equity, US options, crypto)
   - Symbol(s)
   - Side (buy / sell)
   - Quantity or notional amount
   - Order type (market, limit, stop, stop_limit, trailing_stop)
   - Time-in-force (day, gtc, ioc, fok, opg, cls)
   - Limit price and/or stop price if applicable
   - Extended-hours flag
   - Risk controls (max position size, max notional, stop-loss, take-profit)
   - Margin usage

4. **Confirm which paper account is being used.** Your agent verifies that the paper account's configuration meets the strategy's requirements — options approval level, crypto enabled, margin vs cash account, PDT status. It does not assume features are enabled without checking.

5. **Show a complete order preview table before submission.** Every order gets a visual preview with all parameters displayed, estimated notional, and buying power check. No order is ever submitted without a preview.

6. **Ask about confirmation preference.** Your agent asks whether you want explicit confirmation before each order submission, or whether you prefer auto-submit mode. It respects your preference for the session. Default: confirmation ON.

7. **Submit the order to the paper-trading environment only.** Your agent verifies the environment is paper before every submission. It never submits to live.

8. **Return complete post-submission details.** After submission, your agent returns the order ID, status, submitted payload summary, and next inspection steps.

9. **Monitor and update on order lifecycle.**
   - **Filled** → how many shares/contracts, at what price, and how the fill changes portfolio risk.
   - **Partially filled** → current fill vs remaining quantity, average fill price so far.
   - **Rejected** → the rejection reason and specific remediation suggestions.
   - **Canceled** → who canceled (you, system, broker) and why.

10. **Never place live trades.** If live credentials are detected — base URL without the `paper-` prefix, or a profile set to live — your agent stops immediately and warns you. This is a hard block, not a soft warning.

---

## 1 - Prerequisites

- **Alpaca paper-trading account** — free at [alpaca.markets](https://alpaca.markets)
- **Paper API key and secret key** stored in environment variables (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`) or SDK/CLI profile — never pasted into chat
- **Paper base URL**: `https://paper-api.alpaca.markets` (for REST) or appropriate SDK configuration pointing to the paper environment
- **For options**: options trading must be enabled on the paper account with the appropriate approval level (level 1 for covered calls and cash-secured puts, level 2 to buy calls and puts, level 3 for spreads and straddles)
- **For crypto**: crypto trading must be enabled on the paper account
- **SDK / language runtime** (choose one):
  - Python 3.10+ with `alpaca-py` (recommended)
  - JavaScript/TypeScript with `@alpacahq/alpaca-trade-api` (v4+, first-party and actively maintained)
  - Go with `github.com/alpacahq/alpaca-trade-api-go/v3` — the `/v3` suffix is required; without it you pull the v1 path
  - C# with `Alpaca.Markets` (first-party). Community SDKs exist for Java and others.
  - Direct REST API calls via `curl`, `httpx`, `requests`, or any HTTP client
- **Network access** to Alpaca APIs (`paper-api.alpaca.markets`)

---

## 2 - Gather inputs

### Required inputs

| Input | Description | Default |
|---|---|---|
| `signal_source` | Where the trade idea comes from (backtest, manual, automation) | Must be provided |
| `symbol` | Ticker symbol (e.g., `AAPL`, `BTC/USD`, `AAPL250718C00200000` for options) | Must be provided |
| `side` | `buy` or `sell` | Must be provided |
| `qty_or_notional` | Number of shares/contracts OR dollar amount (use `qty` for shares/contracts, `notional` for dollar amount) | Must be provided |
| `order_type` | `market`, `limit`, `stop`, `stop_limit`, `trailing_stop` — **supported values vary by asset class, see below** | `market` |
| `time_in_force` | `day`, `gtc`, `ioc`, `fok`, `opg`, `cls` — **supported values vary by asset class, see below** | `day` for equities; `gtc` for crypto |

### Per-asset-class constraints

The API rejects combinations outside this matrix, so your agent validates before submitting rather than after:

| Asset class | Order types | Time-in-force | Order classes |
|---|---|---|---|
| `us_equity` | `market`, `limit`, `stop`, `stop_limit`, `trailing_stop` | `day`, `gtc`, `opg`, `cls`, `ioc`, `fok` | `simple`, `bracket`, `oco`, `oto` |
| `us_option` | `market`, `limit`, `stop`, `stop_limit` (`stop` types single-leg only) | `day`, `gtc` | `simple`, `mleg` |
| `crypto` | `market`, `limit`, `stop_limit` | `gtc`, `ioc` — `stop_limit` is `gtc`-only, and `ioc` applies only to `market` and `limit` | `simple` |

Treat this as guidance for constructing orders, not as a hard pre-submission gate. Alpaca's sources disagree on the options row: the OpenAPI `TimeInForce`/`OrderType` descriptions say `market`/`limit` with `day` only, while the Options Trading page and the Placing Orders matrix both allow `gtc` and both allow `stop`/`stop_limit` on single-leg orders. The two product pages agree against the spec blob, so this table follows them. Default to `day` for options as the conservative choice, but let Alpaca reject rather than pre-blocking something the matrix permits.

Constraints that cut across order type:

- **Extended hours** requires `limit` type with `day` or `gtc` TIF. Everything else is rejected.
- **Trailing stop** accepts only `day` and `gtc`.
- **Notional** orders cannot be combined with `qty` and **cannot be replaced** — cancel and resubmit instead. For equities they additionally require `market` type with `day` TIF; crypto notional orders are market-type and use the crypto TIF set (`gtc`/`ioc`), so the equities `day` restriction does not apply to them.
- **Bracket, OCO, and OTO** are equities-only, require `day` or `gtc`, and do not support extended hours.
- **`mleg`** carries up to 4 legs and is how multi-leg options strategies are expressed.

### Optional inputs

| Input | Description | Default |
|---|---|---|
| `limit_price` | Required for `limit` and `stop_limit` orders | None |
| `stop_price` | Required for `stop` and `stop_limit` orders | None |
| `trail_price` or `trail_percent` | For trailing stop orders (one or the other, not both) | None |
| `extended_hours` | Allow extended-hours execution (equities only; `limit` type with `day` or `gtc` TIF) | `false` |
| `client_order_id` | User-supplied idempotency key (max 128 chars) | Auto-generated UUID |
| `confirmation_mode` | Whether your agent asks for explicit confirmation before each order | `on` |
| `risk_controls` | Max position size, max notional, max loss threshold | None (recommended to set) |
| `asset_class` | `us_equity`, `us_option`, `crypto` | Inferred from symbol format |
| `order_class` | `simple`, `bracket`, `oco`, `oto`, `mleg` — see the per-asset-class matrix above | `simple` |
| `position_intent` | `buy_to_open`, `buy_to_close`, `sell_to_open`, `sell_to_close` (options only) | Inferred from context |

### Strategy confirmation checklist

Before proceeding past the configuration phase, your agent must confirm each of these with you:

- [ ] **Strategy logic interpretation is correct** — the agent's restatement of your strategy matches your intent
- [ ] **Timing** — immediate execution, or scheduled/conditional (e.g., "only if price drops below $180")
- [ ] **Asset class and symbol are correct** — the right ticker, the right contract (for options), the right pair (for crypto)
- [ ] **Order parameters match the strategy intent** — type, side, quantity, prices, TIF all align with what you want
- [ ] **Paper account is configured for this asset class** — options approval, crypto enabled, margin type
- [ ] **Risk controls are set** (or explicitly waived) — you've acknowledged position sizing, stop-loss, and concentration limits

---

## 3 - Source-of-truth references

| Source | URL | Used for |
|---|---|---|
| Trading API overview | https://docs.alpaca.markets/us/docs/trading-api | API capabilities and structure |
| Working with orders | https://docs.alpaca.markets/us/docs/working-with-orders | Order submission, replacement, cancellation |
| Orders on Alpaca | https://docs.alpaca.markets/us/docs/orders-at-alpaca | Order types, TIF values, status lifecycle |
| Paper trading | https://docs.alpaca.markets/us/docs/paper-trading | Paper environment behavior and limitations |
| Working with positions | https://docs.alpaca.markets/us/docs/working-with-positions | Position retrieval and management |
| Working with account | https://docs.alpaca.markets/us/docs/working-with-account | Account state, buying power, day trade count |
| Working with assets | https://docs.alpaca.markets/us/docs/working-with-assets | Tradability checks, asset attributes |
| Options trading | https://docs.alpaca.markets/us/docs/options-trading | Options order specifics, approval levels |
| Crypto trading | https://docs.alpaca.markets/us/docs/crypto-trading | Crypto order specifics, supported pairs |
| Alpaca disclosures | https://alpaca.markets/disclosures | Required disclosure language |

---

## 4 - Workflow

### Phase 1: Strategy Confirmation

**Step 1 — Identify the signal source.**
Your agent determines where the trade idea comes from:
- **Backtest output**: read the run folder (`notes.md`, `summary.json`) to extract the strategy logic, confirmed parameters, and the last signal. Parse the signal for symbol, side, quantity, and any price targets.
- **Manual idea**: you describe the trade in natural language. Your agent extracts the parameters and asks clarifying questions.
- **Automated system**: a webhook, alert, or scheduled trigger. Your agent reads the payload and maps it to order parameters.

**Step 2 — Reiterate the strategy logic.**
Your agent restates the complete strategy interpretation in plain language:
- What triggers a trade (entry condition)
- What exits a trade (exit condition, stop-loss, take-profit)
- Indicator parameters (e.g., "20-day SMA crossover with 50-day SMA")
- Position sizing rules (e.g., "risk 1% of portfolio per trade")
- Any assumptions your agent is making (e.g., "assuming you want to enter at market price")

**Step 3 — Confirm the interpretation.**
Your agent asks you to confirm or correct the restatement. It does not proceed until you confirm. If you correct it, your agent restates the corrected version and asks again.

### Phase 2: Configuration Agreement

**Step 4 — Gather all order parameters.**
Using the inputs table from §2, your agent collects every required and optional parameter. It asks for anything not already specified.

**Step 5 — Show parameter attribution.**
For each parameter, your agent shows:
- The value being used
- Whether it was **provided** by you, **inferred** from context (e.g., asset class from symbol format), or **defaulted** to a standard value

Example:
```
Symbol:        AAPL           (provided)
Side:          buy            (provided)
Quantity:      50 shares      (provided)
Order type:    limit          (provided)
Limit price:   $180.00        (provided)
TIF:           day            (defaulted — standard for equities)
Extended hrs:  false          (defaulted)
Client order:  a7b3c9d1-...   (auto-generated)
```

**Step 6 — Confirm timing.**
Your agent confirms execution timing:
- **Immediate**: submit now, during current market session
- **Scheduled**: submit at a specific time (your agent notes this requires external scheduling)
- **Conditional**: submit only when a condition is met (your agent notes this requires monitoring logic)

If the timing is not immediate, your agent explains what tooling you'd need and whether it can help set it up (see §4 Phase 8 for deployment guidance).

**Step 7 — Confirm asset class specifics.**

For **US Equity**:
- Verify the symbol is tradable via the assets endpoint
- Check fractional share eligibility if quantity includes decimals
- Confirm extended-hours eligibility if `extended_hours` is `true` (only `limit` orders qualify)
- Note T+1 settlement for sell proceeds

For **US Options**:
- Validate the contract symbol follows OCC symbology: `AAPL250718C00200000`
  - Root symbol (AAPL), expiration (250718 = July 18, 2025), call/put (C/P), strike price × 1000 (00200000 = $200.00)
- Confirm expiration date, strike price, and put/call
- Confirm position intent: buy-to-open, buy-to-close, sell-to-open, sell-to-close
- Note the contract multiplier: 1 contract = 100 shares of the underlying
- Confirm the account's options approval level meets the strategy requirements
- Warn about expiration risk if the expiration is within 5 trading days

For **Crypto**:
- Confirm the pair format (e.g., `BTC/USD`, `ETH/USD`)
- Note 24/7 market — no market-hours constraints
- Check minimum order size for the pair
- Confirm the account has crypto trading enabled

**Step 8 — Confirm risk controls.**
Your agent asks about risk controls:
- **Max position size**: maximum number of shares/contracts in a single position
- **Max portfolio allocation**: maximum percentage of portfolio equity in one symbol
- **Stop-loss**: price or percentage at which to exit a losing position
- **Take-profit**: price or percentage at which to take gains

If you haven't set any risk controls, your agent recommends you consider them. It asks whether you want to set them now or proceed without them. If you proceed without them, your agent notes this in the session log.

**Step 9 — Confirm margin usage.**
Your agent checks:
- Margin classification via `account.multiplier` — the account object has no `account_type` field. `1` is a limited-margin, cash-style account; `2` is a Reg T margin account with 2x intraday and overnight buying power; `4` is a PDT account with 4x intraday and 2x overnight
- Whether shorting is permitted (`account.shorting_enabled`), since the strategy may require it
- Current buying power (`account.buying_power`) and, for options, `account.options_buying_power`
- Current equity (`account.equity`)
- If margin is involved, the maintenance margin requirement (`account.maintenance_margin`)

### Phase 3: Paper Account Verification

**Step 10 — Verify the environment is paper.**
Your agent checks the base URL, SDK configuration, or CLI profile to confirm the environment is **paper**, not live.

| Check | Paper | Live (BLOCKED) |
|---|---|---|
| REST base URL | `https://paper-api.alpaca.markets` | `https://api.alpaca.markets` |
| SDK config | `paper=True` or equivalent | `paper=False` or missing |
| CLI profile | paper profile selected | live profile selected |

If live credentials are detected: **STOP immediately.** Your agent displays a clear warning and refuses to proceed. It does not offer to "switch to paper" on your behalf — you must reconfigure your credentials.

**Step 11 — Fetch account status.**
Your agent retrieves the account and verifies:
- `status` is `ACTIVE` or `PAPER_ONLY` — a paper-only account is valid for this skill and must not be blocked
- `trading_blocked` is `false`
- `account_blocked` is `false`
- `trade_suspended_by_user` is `false`
- `buying_power` is sufficient for the planned order
- `multiplier` for margin classification, which is also the only PDT signal available

The Trading API account object carries **no** `pattern_day_trader` or `daytrade_count` field. Your agent must not read them. A `multiplier` of `4` indicates a PDT account; if you need day-trade counts, derive them from `GET /v2/account/activities` rather than the account object.

**Step 12 — Verify options readiness** (if trading options).
- Gate on `options_trading_level`, not `options_approved_level`. The effective level is the **minimum** of `options_approved_level` and the `max_options_trading_level` in account configuration, and Alpaca exposes it directly as `options_trading_level`. An account approved for level 3 but configured to level 1 can only trade level 1.
- Each level includes the ones below it:
  - Level 0: options trading disabled
  - Level 1: sell covered calls, sell cash-secured puts
  - Level 2: buy calls, buy puts
  - Level 3: spreads and straddles
- Alpaca does not offer naked short options at any level. If a strategy requires one, stop and say so rather than looking for a higher level.
- If `options_trading_level` is `0` or below what the strategy needs, your agent stops and explains which level is required and how to request an upgrade

**Step 13 — Verify crypto readiness** (if trading crypto).
- `crypto_status` is `ACTIVE`
- If crypto is not enabled, your agent stops and explains how to enable it on the account

**Step 14 — Show account summary.**
Your agent displays a summary of the account state:

```
┌─────────────────────────────────────────┐
│         PAPER ACCOUNT SUMMARY           │
├──────────────┬──────────────────────────┤
│ Account ID   │ ****-****-****-a1b2     │
│ Status       │ ACTIVE                   │
│ Equity       │ $100,000.00             │
│ Buying Power │ $100,000.00             │
│ Cash         │ $100,000.00             │
│ Positions    │ 3 open                   │
│ Multiplier   │ 2 (Reg T margin)         │
│ Options Lvl  │ 2 (effective)            │
│ Crypto       │ ACTIVE                   │
└──────────────┴──────────────────────────┘
```

### Phase 4: Order Preview

**Step 15 — Build the order payload.**
Your agent constructs the complete API request body with all confirmed parameters. It sets a unique `client_order_id` for idempotency.

**Step 16 — Display the order preview.**
Your agent shows a complete order preview table:

```
┌─────────────────────────────────────────┐
│           ORDER PREVIEW                  │
├──────────────┬──────────────────────────┤
│ Environment  │ PAPER                    │
│ Symbol       │ AAPL                     │
│ Side         │ buy                      │
│ Quantity     │ 10 shares                │
│ Order Type   │ limit                    │
│ Limit Price  │ $185.50                  │
│ Time-in-Force│ day                      │
│ Extended Hrs │ no                       │
│ Client Order │ abc-123-def              │
│ Est. Notional│ ~$1,855.00              │
│ Buying Power │ $98,500.00 (sufficient) │
└──────────────┴──────────────────────────┘
```

For **options**, the preview also shows:
- Contract: `AAPL 07/18/2025 $200 Call`
- Contracts: 2
- Multiplier: 100 shares/contract
- Est. Premium: ~$3.50 × 2 × 100 = $700.00
- Position intent: buy-to-open

For **crypto**, the preview also shows:
- Pair: BTC/USD
- Market: 24/7 (always open)
- Notional: $500.00 (if notional order)

**Step 17 — Confirmation-ON mode.**
If `confirmation_mode` is `on`, your agent asks:

> Submit this order? (yes / no)

It waits for your explicit `yes` before proceeding. Any response other than a clear affirmative is treated as "no" and your agent asks what you'd like to change.

**Step 18 — Confirmation-OFF mode.**
If `confirmation_mode` is `off`, your agent informs you:

> Confirmation mode is OFF. This order will be submitted now. The preview is shown above for your review.

Your agent then proceeds to submission.

### Phase 5: Order Submission

**Step 19 — Submit the order.**
Your agent sends the order to the paper trading API via your chosen execution method (SDK, REST, CLI, or MCP tool). The endpoint is `POST /v2/orders` against the paper base URL.

**Step 20 — Capture the response.**
On success, your agent captures:
- `id` (order ID)
- `client_order_id`
- `status` — usually `new`, meaning Alpaca received the order and routed it. `accepted` means received but not yet routed and is common outside trading hours; `pending_new` and `accepted_for_bidding` are documented as rare
- `created_at`
- `submitted_at`
- `symbol`, `side`, `qty`, `type`, `time_in_force`
- All echoed fields from the API response

**Step 21 — Handle submission failure.**
If the submission fails, your agent:
1. Captures the full error response (HTTP status code, error message, error code)
2. Shows you the error in plain language
3. Suggests specific remediation. `POST /v2/orders` documents exactly two error responses, and they do not mean what their generic HTTP names suggest:
   - `403 Forbidden` → **insufficient buying power or shares**, not an auth problem. Show current buying power versus required, or current position versus the quantity being sold
   - `422 Unprocessable Entity` → input parameters not recognized. Show which ones, and check them against the per-asset-class matrix in section 2
   - `429 Too Many Requests` → rate limited; honor `Retry-After` and back off
   - `401 Unauthorized` → credential problem. Stop; do not retry with the same credentials
   - Network timeout → verify whether the order was received before doing anything else

   A non-tradable or unknown symbol surfaces as `422` from the order endpoint, not `404`. Your agent validates the symbol against `GET /v2/assets/{symbol_or_asset_id}` beforehand, where a genuinely unknown symbol does return `404`. Crypto requires the old symbology without a slash (`BTCUSD`), and any slash that remains must be URL-encoded (`/v2/assets/BTC%2FUSDT`) or the request is malformed.
4. Saves the failed attempt to the session log
5. Does **NOT** automatically retry for non-idempotent submissions. If it's unclear whether the order was received (e.g., network timeout), your agent checks existing orders by `client_order_id` first.

### Phase 6: Post-Submission Monitoring

**Step 22 — Fetch order status.**
Immediately after a successful submission, your agent fetches the order by ID (`GET /v2/orders/{id}`) to confirm the current status.

**Step 23 — Return post-submission summary.**
Your agent shows you:

```
Order submitted successfully.

Order ID:        b1e2f3a4-5678-9012-cdef-abcdef123456
Status:          accepted
Symbol:          AAPL
Side:            buy
Qty:             10
Type:            limit
Limit Price:     $185.50
TIF:             day
Submitted at:    2026-07-26T15:30:00Z
Environment:     PAPER

Next steps:
- Ask me to check the status of this order
- Ask me to cancel this order
- Ask me to show your current positions
- Ask me to show your portfolio summary
```

**Step 24 — Order lifecycle updates.**

Your agent tracks the order through its lifecycle and reports each transition:

**Filled:**
```
✅ Order FILLED

Order ID:        b1e2f3a4-...
Symbol:          AAPL
Side:            buy
Filled Qty:      10 shares
Avg Fill Price:  $185.32
Fill Time:       2026-07-26T15:30:05Z

Portfolio impact:
- AAPL position:   10 shares @ $185.32 (new position)
- Position value:   $1,853.20
- Portfolio %:      1.85% of equity
- Buying Power:     $98,146.80 (was $100,000.00)
```

**Partially filled:**
```
⏳ Order PARTIALLY FILLED

Order ID:        b1e2f3a4-...
Filled:          6 of 10 shares
Avg Fill Price:  $185.35
Remaining:       4 shares (still working)
```

**Rejected:**
```
❌ Order REJECTED

Order ID:        b1e2f3a4-...
Reason:          insufficient buying power
Details:         Required ~$1,855.00, available $500.00

Remediation:
- Reduce order quantity
- Close existing positions to free buying power
- If this is unexpected, check your account for pending orders
  consuming buying power
```

**Canceled:**
```
🚫 Order CANCELED

Order ID:        b1e2f3a4-...
Canceled by:     system
Reason:          day order expired at market close (16:00 ET)

If you still want this position, consider:
- Resubmitting as a GTC order
- Waiting for the next market open
```

**Replaced:**
```
🔄 Order REPLACED

Old Order ID:    b1e2f3a4-...
New Order ID:    c2d3e4f5-...
Changed:
  Limit Price:   $185.50 → $186.00
  Quantity:      10 → 15
```

### Phase 7: Portfolio Impact Assessment

**Step 25 — Fetch updated positions and account.**
After a fill, your agent retrieves the current positions (`GET /v2/positions`) and account (`GET /v2/account`) to show the impact.

**Step 26 — Show portfolio risk summary.**
```
┌─────────────────────────────────────────┐
│        PORTFOLIO RISK SUMMARY           │
├──────────────┬──────────────────────────┤
│ Total Equity │ $100,050.00             │
│ Buying Power │ $98,146.80              │
│ Open Pos.    │ 4 positions              │
│ Open Orders  │ 1 working                │
│                                         │
│ Position Concentration:                 │
│   AAPL       │  1.85% ($1,853.20)      │
│   MSFT       │  3.20% ($3,201.00)      │
│   TSLA       │  2.10% ($2,100.50)      │
│   BTC/USD    │  5.00% ($5,002.30)      │
│                                         │
│ Unrealized P&L (total): +$50.00        │
└──────────────┴──────────────────────────┘
```

- **Position concentration**: `abs(position.market_value) / equity × 100` — the Position field is `market_value`. (`position_market_value` exists only on the account payload as an all-positions aggregate.)
- **Unrealized P&L**: `(current_price - avg_entry_price) × qty`
- **Day trade count**: relevant for equity accounts with less than $25k equity
- **Open orders**: orders still working that may consume additional buying power

### Phase 8: Deployment Guidance

> This phase is optional. Your agent provides this guidance only when you ask about deploying or automating a strategy.

**Step 27 — Provide deployment options.**

If you ask how to deploy or automate the strategy, your agent outlines these paths:

**Local scheduler:**
- Use `cron` (Linux/macOS), `launchd` (macOS), or Windows Task Scheduler
- Write a Python script using `alpaca-py` that encapsulates the strategy logic
- Schedule it to run at your desired frequency
- Log output to a file for review

**Cloud hosting:**
- AWS Lambda + EventBridge for serverless scheduled execution
- Google Cloud Functions + Cloud Scheduler
- Railway, Render, or Fly.io for persistent process hosting
- Any platform that can run a Python/Node.js process on a schedule

**Webhook-based:**
- TradingView alerts → webhook endpoint → your server → Alpaca API
- Custom alert system → webhook → order execution logic

**Every deployed path asserts paper at startup.** Scheduling, hosting, and webhook triggers differ, but they share one requirement: the artifact that runs unattended proves it is pointed at paper before it can place an order, and exits if it cannot. There is no operator watching to catch a wrong endpoint, and a live account returns the same response shape as a paper one, so nothing downstream will reveal the mistake.

Two rules make that assertion trustworthy:

- **Pin the paper endpoint as a literal in code, not as configuration.** An endpoint read from an environment variable, a config file, or a CI secret can be changed by someone who never reads this skill. In `alpaca-py` that means constructing the client as `TradingClient(key, secret, paper=True)` with `paper=True` written literally, never `paper=os.getenv(...)`.
- **Abort on any signal that live was intended.** If a live endpoint, a live-trading flag, or a live profile is present in the environment, exit non-zero before the first order rather than resolving the conflict silently.

Naming a credential or variable "paper" is not evidence. Only the resolved endpoint is.

**Important notes your agent always includes:**
- Validate any new automation against paper for a meaningful period before considering live at all
- Your agent does not recommend any specific hosting provider or guarantee uptime
- Automating live trading is a separate, significant decision with additional regulatory and risk considerations
- Monitor automated systems regularly — do not "set and forget"
- Include error handling, logging, and alerting in any automated system
- Consider what happens when your automation encounters an unexpected market condition

---

## 5 - Execution rules

### Environment safety

- This skill operates in the **paper-trading environment ONLY**.
- If your agent detects live API credentials — base URL is `https://api.alpaca.markets` without the `paper-` prefix, or the SDK/CLI profile is set to live — it must **STOP** and warn you immediately.
- Your agent must verify the environment before **every** order submission, not just once per session. Environment state can change if credentials are reconfigured mid-session.
- Your agent never offers to "switch to live" or facilitate the transition from paper to live trading.

### Confirmation behavior

- At the start of each session, your agent asks whether you want explicit confirmation before each order (default: **ON**).
- In **confirmation-ON** mode, your agent shows the order preview and waits for your explicit "yes" before submitting.
- In **confirmation-OFF** mode, your agent still shows the order preview but submits after a brief display pause. It announces the submission clearly.
- You can toggle confirmation mode at any time during the session by telling your agent.
- Regardless of mode, your agent **always** shows the order preview. It never submits silently.

### Idempotency

- Your agent sets a unique `client_order_id` on every order to prevent duplicate submissions.
- If submission fails with a network error and it's unclear whether the order was received, your agent checks existing orders for the `client_order_id` before retrying.
- `client_order_id` values are logged in the session's `orders.json` for audit.

### Rate limiting

- Drive throttling from the response headers rather than a hard-coded ceiling. Every response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`; your agent slows down as `Remaining` approaches zero instead of waiting to be throttled. A figure of 200 requests per minute is widely cited for the Trading API but is not stated in Alpaca's current documentation, so do not hard-code it.
- If rate-limited (HTTP 429), stop and retry with exponential backoff plus jitter (1s, 2s, 4s, 8s, capped), and do not retry before the time given by `X-RateLimit-Reset`.
- Do not spam order status checks. Poll at reasonable intervals:
  - Active market order: every 2 seconds for the first 10 seconds, then every 5 seconds
  - Active limit order: every 5 seconds for the first minute, then every 30 seconds
  - No order should be polled more than 60 times total

### Asset class rules

**US Equity:**
- Standard market hours: 9:30 AM–4:00 PM ET
- Extended hours require `extended_hours: true` on a `limit` order with `day` or `gtc` TIF, and cover three sessions:
  - Overnight: 8:00 PM–4:00 AM ET, Sunday to Friday
  - Pre-market: 4:00 AM–9:30 AM ET, Monday to Friday
  - After-hours: 4:00 PM–8:00 PM ET, Monday to Friday
- Not every asset is eligible for the overnight session — confirm on the asset record rather than assuming
- Fractional shares supported for eligible symbols (check `fractionable` attribute)
- T+1 settlement — sell proceeds are available the next business day
- Short selling requires a margin account and locatable shares

**US Options:**
- Standard market hours: 9:30 AM–4:00 PM ET
- One contract = 100 shares of the underlying
- Approval level required (1, 2, or 3) — verify before submitting
- Exercise and assignment are automatic at expiration for ITM options
- Options have expiration dates — they lose value over time (theta decay)
- American-style options can be exercised any time before expiration
- Weekly, monthly, and quarterly expirations available for major symbols

**Crypto:**
- 24/7 market — no market-hours constraints
- Minimum order sizes apply per pair (check the asset endpoint)
- Not all pairs are available — verify before submitting
- No extended-hours concept — always open
- Fractional quantities supported for most pairs
- No short selling of crypto

### Error handling

- **Auth failure (401):** Stop, show the error, suggest re-authenticating. Never retry with the same credentials.
- **Insufficient buying power or shares (403):** On `POST /v2/orders`, `403` means the tradable balance or share count is insufficient — it is not an auth failure. Show current buying power, required notional, and the shortfall. Suggest reducing quantity or closing positions.
- **Non-tradable symbol (422):** The order endpoint reports unrecognized input as `422`. Show the asset status and suggest checking the symbol. Offer to search for the correct symbol. `GET /v2/assets/{symbol_or_asset_id}` is the place a `404` legitimately appears.
- **Market closed (422):** Show current market status and next open time using the clock endpoint (`GET /v2/clock`).
- **Rate limit (429):** Wait and retry with exponential backoff. Inform you of the delay.
- **Network timeout:** Check if the order was received (by `client_order_id`) before deciding whether to retry.
- **Unknown error:** Show the full error response. Do not silently swallow errors. Log the error to the session file.

---

## 6 - Output contract

### In-chat response after submission

```
Order submitted successfully.

Order ID:        {order_id}
Status:          {status}
Symbol:          {symbol}
Side:            {side}
Qty:             {qty}
Type:            {order_type}
TIF:             {time_in_force}
Submitted at:    {submitted_at}
Environment:     PAPER

Next steps:
- Ask me to check the status of this order
- Ask me to cancel this order
- Ask me to show your current positions
- Ask me to show your portfolio summary
```

### Run folder artifacts

When the skill is used as part of a session with multiple orders, your agent writes session artifacts to a run folder:

```
runs/<YYYYMMDD-HHMMSS>-paper-trading/
  notes.md              # strategy context, confirmation choices, assumptions
  orders.json           # all orders submitted in this session
  order_log.csv         # timeline: order_id, timestamp, event, status, details
  positions_snapshot.json # positions after last fill
  portfolio_summary.md  # human-readable portfolio state
  review.md             # session review and open questions
```

**File descriptions:**

| File | Content | Format |
|---|---|---|
| `notes.md` | Strategy description, signal source, confirmation preferences, assumptions made, risk controls applied | Markdown |
| `orders.json` | Array of all orders submitted, including request payload and response | JSON |
| `order_log.csv` | Chronological event log: `order_id, timestamp, event_type, status, details` | CSV |
| `positions_snapshot.json` | Positions at the end of the session (from `GET /v2/positions`) | JSON |
| `portfolio_summary.md` | Human-readable portfolio state: equity, buying power, positions, concentration, P&L | Markdown |
| `review.md` | Session review: what worked, what didn't, open questions, suggested improvements | Markdown |

---

## 7 - Validation and tests

Validate behavior against:
- Happy path scenarios for each asset class
- Missing and ambiguous input handling
- Auth and permission failure handling
- Environment safety verification (live credential detection)
- Order lifecycle transitions
- Edge cases: insufficient buying power, non-tradable symbols, market-closed, PDT warnings
- Idempotency and network failure recovery
- Confirmation mode switching

Run these tests mentally or against a paper account whenever modifying this skill.

---

## 8 - Disclosures, safety, and data handling

### Required disclosure

> **Important disclosure:** This material is for informational, educational, and research purposes only. It is not investment advice, a recommendation, an offer, or a solicitation to buy or sell securities, options, cryptocurrencies, or any other financial product. All investing and trading involve risk, including possible loss of principal. Paper trading is simulated and may differ from live trading in fills, market impact, liquidity, fees, latency, and other factors. Review Alpaca's disclosures at https://alpaca.markets/disclosures.

Your agent includes this disclosure in every session summary, report, and portfolio review.

### Paper-trading specific

- Paper trading results are simulated. They do not represent actual trading performance.
- Paper fills may differ from live fills in price, timing, partial fills, and rejection behavior.
- Paper trading does not charge real commissions or fees. Live trading may incur costs.
- Moving from paper to live trading is a separate, significant decision that requires additional review of risk tolerance, capital adequacy, and regulatory requirements.
- This skill will never facilitate that transition directly.

### Options-specific

When options are involved, your agent includes:

- Options involve significant risk and are not suitable for all investors.
- Options can expire worthless. You can lose the entire premium paid for long options.
- Selling options carries risk that can exceed the premium received, and assignment can force a position at an unfavorable price.
- Complex options strategies (spreads, straddles, strangles) carry additional risks and may have multiple legs with different outcomes.
- Options are subject to exercise and assignment risk, especially near expiration.
- Understand the Greeks (delta, gamma, theta, vega) and how they affect your position before trading.

### Crypto-specific

When crypto is involved, your agent includes:

- Cryptocurrency trading involves substantial risk due to high volatility.
- Crypto assets are not securities and may have different regulatory protections than traditional securities.
- Crypto markets operate 24/7 and can experience significant price swings at any time.
- Crypto assets are not FDIC insured or SIPC protected.
- Regulatory environment for crypto is evolving and may change.

### Credentials and data handling

- Your agent reads credentials from environment variables (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`), SDK configuration files, or CLI profile settings.
- **Never** paste API keys or secrets into chat. Your agent will refuse to accept them if offered.
- Your agent redacts account IDs, order IDs, and personally identifiable information in any summaries shared outside the session.
- Raw API responses are stored locally only (in the run folder) and classified as account-level confidential.
- Your agent does not send trading data, account data, or credentials to any third party.
- Session artifacts (run folder files) remain on your local filesystem. Review and delete them as appropriate.

---

## 9 - Anti-patterns

- **NEVER** submit orders to a live trading environment. This skill is paper-only.
- **NEVER** ask for API keys or secrets in chat. Credentials come from environment variables or config files.
- **NEVER** print credentials, tokens, account numbers, or profile details in plain text.
- **NEVER** skip the order preview — always show it, regardless of confirmation mode.
- **NEVER** retry a failed order submission without first checking if the original was received (use `client_order_id` for idempotency).
- **NEVER** give investment advice, recommend specific securities, or imply a strategy is suitable, profitable, or low-risk.
- **NEVER** assume the paper account has specific features enabled (options, crypto, margin) without checking the account endpoint.
- **NEVER** hide order parameters, defaults, or execution assumptions from you.
- **NEVER** treat paper trading results as proof or prediction of live trading performance.
- **NEVER** auto-submit orders in a loop without user awareness — if placing bulk orders, preview each one (or show a summary table of all orders and get batch confirmation).
- **NEVER** assume market hours — always check the clock/calendar endpoint before submitting time-sensitive orders.
- **NEVER** mix paper and live credentials in the same session.
- **NEVER** place orders for asset classes you haven't confirmed you want to trade.

---

## 10 - Related files

| File | Description |
|---|---|
| `reference.md` | API endpoint details, order schemas, status lifecycle diagrams, error codes |

### Companion skills

| Skill | Description |
|---|---|
| `alpaca-trading-paper-trading-cli` | CLI-specific version using the Alpaca CLI |
| `alpaca-trading-paper-trading-mcp` | MCP-specific version using Trading API MCP tools |

### Related skills

| Skill | Description |
|---|---|
| `alpaca-trading-backtest` | Run historical backtests that produce signals for this skill |
