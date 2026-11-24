---
name: alpaca-trading-paper-trading-mcp
description: >
  Preview, submit, inspect, and manage Alpaca paper-trading orders using
  Trading API MCP. Supports US equities, options, and crypto.
  Use this skill when you want your AI agent to execute paper trades through
  MCP tool calls — no CLI installation or direct API coding required.
---

# Alpaca Paper Trading — Trading API MCP Version

Use this skill when you want your AI agent to preview, submit, inspect, and manage paper-trading orders using Trading API MCP.

This skill is written for you, a Trading API user working with your own Alpaca paper-trading account. Your agent calls MCP tools directly — no CLI installation or raw HTTP requests needed. The MCP server handles authentication and API communication.

This is the Trading API MCP version. A generic (implementation-agnostic) version and a CLI version are also available as companion skills.

---

## 0 — How your AI agent should use this skill

1. **Start with the signal source.** Whether it originates from a backtest result, a manual trading idea, a scheduled trigger, or a conversational request — identify what is driving the trade.
2. **Reiterate strategy logic and confirm with you.** Your agent must restate the trading idea in its own words and wait for your confirmation before proceeding.
3. **Gather and confirm ALL configurations.** Timing, asset class, symbol, side, quantity or notional amount, order type, time-in-force, limit/stop prices, extended-hours flag, risk controls (position limits, max order size, loss thresholds), and margin intent.
4. **Discover available MCP tools.** Your agent must call `GetDynamicTools` to find the Trading API MCP namespace and inspect available tool schemas before calling any tool. Tool names and parameters vary by MCP server implementation — never assume.
5. **Verify paper environment.** Read `env.ALPACA_PAPER_TRADE` from the host's MCP config file — no tool exposes it — and require it to be absent, `true`, `1`, or `yes`. Then confirm the account is active and unblocked. If paper mode cannot be proven, **STOP immediately** and tell you.
6. **Show a complete order preview table.** Every parameter that will be sent to the order-placement tool must be visible to you before submission.
7. **Ask whether you want explicit confirmation before each order** (default: ON). Respect your preference for the rest of the session.
8. **Submit via the order-placement tool for the asset class.** Placement is split across stock, crypto, and option tools — select by asset class, then pass the confirmed parameters exactly as previewed.
9. **Monitor with the order lookup and order list tools.** Report fills, rejections, partial fills, and portfolio impact.
10. **Never place live trades.** Verify paper environment before every submission.

---

## 1 — Prerequisites

### Required

- **Trading API MCP** installed and configured in your agent host (Cursor, etc.)
- **Paper trading API key and secret** configured as environment variables in the MCP server configuration — **never** pasted into chat or passed as tool arguments
- MCP server namespace discoverable via `GetDynamicTools`
- Paper trading account active at Alpaca

### Conditional

- **Options trading**: must be enabled on your Alpaca paper account
- **Crypto trading**: must be enabled on your Alpaca paper account

### MCP Server Setup (Cursor)

The server is Trading API MCP, Alpaca's official MCP server, maintained at [alpacahq/alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server). That repository's README is the source of truth for the package name, command, and environment variables. The configuration below reflects v2.

Add it to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "alpaca-paper-trading": {
      "command": "uvx",
      "args": ["alpaca-mcp-server"],
      "env": {
        "ALPACA_API_KEY": "your-paper-key",
        "ALPACA_SECRET_KEY": "your-paper-secret",
        "ALPACA_PAPER_TRADE": "true"
      }
    }
  }
}
```

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ALPACA_API_KEY` | Yes | — | Paper API key |
| `ALPACA_SECRET_KEY` | Yes | — | Paper secret key |
| `ALPACA_PAPER_TRADE` | No | `true` | Paper/live switch; `false` selects live. This skill requires `true`. |
| `ALPACA_TOOLSETS` | No | all | Comma-separated toolsets to expose. Leaving it unset means you have all capabilities. Set it (for example `account,trading,assets`) only to narrow what the agent can reach. |

Paper versus live is determined solely by `ALPACA_PAPER_TRADE`. The server derives the API host from that flag, so there is no base-URL variable to set and none to verify.

### Verifying the MCP server is available

Your agent should run:

```
GetDynamicTools with pattern "alpaca"
```

If the namespace is not found, appears in `"error"` or `"loading"` state, or has `namespaceStatus: "needsAuth"`:

1. If `"needsAuth"` — authenticate via `mcp_auth` for that namespace, then retry.
2. If `"error"` or not found — tell you to check the MCP server configuration in Cursor settings.
3. Do **not** fall back to direct HTTP calls or CLI commands. This is the MCP version.

---

## 2 — Gather inputs

### Input table

| Parameter | Required | Default | Notes |
|---|---|---|---|
| `symbol` | Yes | — | Ticker symbol (e.g., `AAPL`, `BTC/USD`, `AAPL251219C00250000`) |
| `side` | Yes | — | `buy` or `sell` |
| `qty` | One of qty/notional | — | Number of shares/units. Whole or fractional. Mutually exclusive with `notional` |
| `notional` | One of qty/notional | — | Dollar amount. Stocks: market orders with `day` TIF only. Crypto: market orders only. Not available on `place_option_order` |
| `type` | No | `market` | Stocks: `market`, `limit`, `stop`, `stop_limit`, `trailing_stop`. Crypto: `market`, `limit`, `stop_limit`. Options: `market`, `limit`. **The parameter is `type`, not `order_type`** |
| `time_in_force` | No | `day` (stocks), `gtc` (crypto), `day` (options) | Stocks: `day`, `gtc`, `opg`, `cls`, `ioc`, `fok`. Crypto: `gtc` or `ioc` only — `day` and `fok` are rejected. Options: `day` only |
| `limit_price` | If limit/stop_limit | — | Limit price |
| `stop_price` | If stop/stop_limit | — | Stop trigger price |
| `trail_percent` | If trailing_stop | — | Trailing stop percentage. `place_stock_order` only |
| `trail_price` | If trailing_stop | — | Trailing stop dollar offset. `place_stock_order` only |
| `extended_hours` | No | `false` | Allow extended-hours fills. `place_stock_order` only; `limit` type with `day` or `gtc` TIF |
| `client_order_id` | No | Alpaca generates one if omitted | Idempotency key — your agent generates one per order |
| `order_class` | No | `null` | `simple`, `bracket`, `oco`, `oto`. `place_stock_order` only. Automatically set to `bracket` when either bracket-leg parameter below is supplied |
| `take_profit_limit_price` | If bracket | — | Limit price for the take-profit leg. `place_stock_order` only |
| `stop_loss_stop_price` | If bracket | — | Stop price for the stop-loss leg. `place_stock_order` only |
| `stop_loss_limit_price` | No | — | Limit price for the stop-loss leg. Requires `stop_loss_stop_price` |
| `position_intent` | No | — | `buy_to_open`, `buy_to_close`, `sell_to_open`, `sell_to_close` (options) |

> The bracket legs are **flat scalar parameters**, not nested objects. `POST /v2/orders` takes nested `take_profit: { limit_price }` and `stop_loss: { stop_price, limit_price }`, but the `place_*` tools flatten them, and their schemas set `additionalProperties: false` — so passing the nested REST shape is a hard rejection, not a silently ignored field. This is the general hazard: the tools deliberately reshape the REST body, so never build parameters from the REST schema.

### Additional context gathered

| Input | Required | Default | Notes |
|---|---|---|---|
| `asset_class` | Inferred | `us_equity` | `us_equity`, `crypto`, `us_option` |
| `strategy_description` | Recommended | — | Natural-language description of the trade rationale |
| `risk_controls` | Recommended | — | Max position size, max loss threshold, portfolio concentration limit |
| `mcp_namespace` | Discovered | — | The MCP namespace where Alpaca tools are available (via `GetDynamicTools`) |

### Strategy confirmation checklist

Before proceeding to order preview, your agent must confirm:

- [ ] Strategy intent restated in plain language
- [ ] Symbol, side, and quantity/notional confirmed
- [ ] Order type and all price levels confirmed
- [ ] Time-in-force confirmed
- [ ] Extended-hours intent confirmed (equities)
- [ ] Risk controls confirmed (or explicitly waived)
- [ ] Asset-class-specific requirements confirmed (options approval, crypto eligibility)
- [ ] Paper environment verified

---

## 3 — Source-of-truth references

| Source | URL | Used for |
|---|---|---|
| Trading API MCP | https://github.com/alpacahq/alpaca-mcp-server | Server setup, environment variables, toolsets, current tool list |
| Alpaca Trading API docs | https://docs.alpaca.markets/us/docs/trading-api | Order parameters, account fields, asset details |
| Create Order reference | https://docs.alpaca.markets/us/reference/postorder | Underlying REST semantics only — **not** the tool parameter shape. The `place_*` tools flatten and constrain this schema, so always build parameters from the discovered tool schema |
| Order types guide | https://docs.alpaca.markets/us/docs/orders-at-alpaca | Order type behavior, TIF rules, extended hours |
| Options trading | https://docs.alpaca.markets/us/docs/options-trading | Options order requirements, exercise/assignment |
| Crypto trading | https://docs.alpaca.markets/us/docs/crypto-trading | Crypto pairs, 24/7 trading, fractional units |
| Account API | https://docs.alpaca.markets/us/reference/getaccount-1 | Account status fields, buying power, PDT |
| Alpaca disclosures | https://alpaca.markets/disclosures | Disclosure language |

### Discovery rule

Your agent **must** call `GetDynamicTools` to discover the actual MCP namespace, tool names, and parameter schemas before calling any tool. The names this skill cites are those of the official server at v2; confirm them, and never assume a parameter format.

---

## 4 — Workflow

### Phase 1: Strategy Confirmation

**Step 1** — Identify the signal source.

Determine where the trade idea originates:
- Backtest result (reference the run folder and signal)
- Manual idea from you ("I want to buy 100 shares of AAPL")
- Scheduled or conditional trigger ("Buy when AAPL drops below $180")
- Portfolio rebalance ("Close my TSLA position and rotate into NVDA")

**Step 2** — Reiterate the strategy.

Your agent restates the trade in its own words:

> "You want to buy 10 shares of AAPL as a market order, good for the day, in your paper account. This is a manual directional trade — no stop loss or take profit attached. Is that correct?"

**Step 3** — Wait for your confirmation.

Do not proceed until you confirm. If you correct any detail, your agent re-confirms the updated version.

### Phase 2: Configuration Agreement

**Step 4** — Gather all order parameters from the input table above.

**Step 5** — For limit, stop, or bracket orders, confirm all price levels.

**Step 6** — Confirm time-in-force and extended-hours settings.

**Step 7** — Confirm risk controls:
- Maximum position size in this symbol
- Maximum single-order notional value
- Portfolio concentration limits
- Stop-loss or take-profit levels (if bracket)

**Step 8** — For options: confirm the contract symbol, position intent (`buy_to_open`, etc.), and that options trading is enabled.

**Step 9** — For crypto: confirm the trading pair (e.g., `BTC/USD`), quantity precision, and 24/7 availability.

### Phase 3: MCP Discovery and Paper Account Verification

**Step 10** — Discover the Trading API MCP namespace.

```
Call GetDynamicTools with pattern "alpaca" to find the namespace.
Then call GetDynamicTools with the found namespace to list all available tools.
```

Your agent inspects the available tools and their parameter schemas. This step must happen every session — tool names and schemas may change between MCP server versions.

**Step 11** — Fetch account status via MCP.

Call the account-info tool — `get_account_info` as of v2; confirm the name against discovery.

From the response, verify:
- `status` = `ACTIVE`
- `trading_blocked` = `false`
- `account_blocked` = `false`

Paper mode itself is established by the server's `ALPACA_PAPER_TRADE` setting, not by these fields.

**Step 12** — **STOP gate**: prove paper mode from the MCP client config, then stop if you cannot.

The MCP server does **not** expose `ALPACA_PAPER_TRADE` to your agent. There is no tool, resource, or server-instruction field that reports it, so the agent cannot ask the server which mode it is in. The only place that value is readable is the client's own MCP configuration file.

That file also holds `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in the same `env` block, so your agent **must not read the file as a whole** — no `cat`, no file-read tool, no printing the server entry. Reading it wholesale would pull the credentials into model context and violate the data-handling guarantee in §8. The gate needs exactly one value, so it extracts exactly that one value:

```bash
# 1. List server names (names are not secrets)
jq -r '.mcpServers | keys[]' ~/.cursor/mcp.json

# 2. Confirm the chosen entry exists, then read only the flag
jq -r '.mcpServers | has("<server-name>")' ~/.cursor/mcp.json
jq -r '.mcpServers["<server-name>"].env.ALPACA_PAPER_TRADE // "unset"' ~/.cursor/mcp.json
```

On a host without `jq`, the equivalent single-value read:

```bash
python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));e=d["mcpServers"][sys.argv[2]].get("env") or {};print(e.get("ALPACA_PAPER_TRADE","unset"))' ~/.cursor/mcp.json '<server-name>'
```

Substitute the host's own config path when it is not Cursor. Your agent then:

1. Identifies the server entry backing the namespace it discovered its Alpaca tools from, and confirms that entry exists — step 2 above.
2. Requires the flag to be `unset`, or set to `true`, `1`, or `yes` (case-insensitive). The server lowercases the value and tests membership in exactly that set, so **any other value selects live** — including `paper`, `TRUE ` with a trailing space, and `yes!`.

Distinguish the two ways a read comes back empty, because they are not equivalent. A confirmed entry whose flag is `unset` **passes** — the server defaults to paper when the variable is absent. An entry that cannot be found, or a config that cannot be parsed, is an **inconclusive** read, not a passing one, and the value printed for it is indistinguishable from a genuinely absent flag. Never let the second case be read as the first.

If the config cannot be read or parsed, the server entry cannot be identified, or the value is anything outside that set, the gate **fails closed**. Your agent stops and tells you:

> "⚠️ I cannot confirm this MCP server is in paper mode. This skill only supports paper trading. Check that `ALPACA_PAPER_TRADE` is `true` in the server's `env` block and that the configured keys are paper keys, then restart the client."

Your agent must never treat the account response as proof. Live and paper accounts return the same shape, so an account payload can never by itself establish the environment — treat unproven as live. Two weaker signals may *corroborate* a passing config check but must never substitute for it: paper accounts commonly return an `account_number` beginning `PA`, and `status` may be `PAPER_ONLY`. Neither is a documented guarantee.

Do not proceed under any circumstances if paper mode is unproven.

**Step 13** — From the account response, check:
- `buying_power` — sufficient for the planned order
- `options_trading_level` — if trading options. This is the effective level (the minimum of `options_approved_level` and the configured `max_options_trading_level`), so gate on it rather than on `options_approved_level`
- `options_buying_power` — if trading options
- `crypto_status` — if trading crypto
- `multiplier` — margin classification, and the only PDT signal the account object carries: `4` means a PDT account

The account object has no `pattern_day_trader`, `daytrade_count`, or `daytrading_buying_power` field. Your agent must not read them.

**Step 14** — Show account summary:

```
┌─────────────────────────────────────────┐
│         Paper Account Summary           │
├─────────────────────┬───────────────────┤
│ Account ID          │ xxxxxxxx          │
│ Status              │ ACTIVE            │
│ Environment         │ PAPER             │
│ Equity              │ $100,000.00       │
│ Buying Power        │ $200,000.00       │
│ Cash                │ $100,000.00       │
│ Options Approved    │ Level 2           │
│ Crypto Status       │ ACTIVE            │
│ PDT                 │ No                │
└─────────────────────┴───────────────────┘
```

### Phase 4: Order Preview

**Step 15** — Build the order parameters object. Do NOT call the submit tool yet.

Construct the exact parameter set that will be sent to the order-placement tool selected in Step 19:

```json
{
  "symbol": "AAPL",
  "side": "buy",
  "qty": "10",
  "type": "limit",
  "limit_price": "185.50",
  "time_in_force": "day",
  "client_order_id": "pt-20260726-001-aapl-buy"
}
```

**Step 16** — Display the order preview:

```
┌─────────────────────────────────────────┐
│           ORDER PREVIEW                 │
├─────────────────────┬───────────────────┤
│ Symbol              │ AAPL              │
│ Side                │ BUY               │
│ Quantity            │ 10 shares         │
│ Order Type          │ LIMIT             │
│ Limit Price         │ $185.50           │
│ Time in Force       │ DAY               │
│ Extended Hours      │ No                │
│ Order Class         │ Simple            │
│ Est. Notional       │ $1,855.00         │
│ Client Order ID     │ pt-20260726-...   │
│ Environment         │ PAPER (verified)  │
├─────────────────────┴───────────────────┤
│ ⚠ Paper trading only. Not financial    │
│   advice. Past performance ≠ future.   │
└─────────────────────────────────────────┘
```

**Step 17** — If confirmation is ON (default): wait for your explicit "yes" or "go ahead" before submitting.

**Step 18** — If you previously set confirmation to OFF: show the preview, pause briefly to let you read it, then proceed.

### Phase 5: Order Submission via MCP

**Step 19** — Select the order-placement tool for the asset class, then call it.

There is no single create-order tool. Placement is split by asset class, so the tool is chosen from the asset class confirmed in Step 7:

| Asset class | Tool (as of v2) | Supports |
|---|---|---|
| US equity / ETF | `place_stock_order` | market, limit, stop, stop-limit, trailing-stop, brackets |
| Crypto | `place_crypto_order` | market, limit, stop-limit |
| US option | `place_option_order` | single-leg and multi-leg |

Each takes its own schema — the order types available for stocks are not all available for crypto, so read the schema of the specific tool you selected rather than reusing parameters from another. Confirm the name and parameters against discovery before calling; the names above are current for v2 and are not guaranteed across versions.

```
Call place_stock_order with:
  symbol: "AAPL"
  side: "buy"
  qty: "10"
  type: "limit"
  limit_price: "185.50"
  time_in_force: "day"
  client_order_id: "pt-20260726-001-aapl-buy"
```

**Step 20** — Parse the response.

Extract from the MCP response:
- `id` — the Alpaca order ID
- `client_order_id` — your idempotency key
- `status` — initial order status (`new`, `accepted`, `pending_new`)
- `created_at` — submission timestamp
- `filled_qty`, `filled_avg_price` — if immediately filled (market orders)

**Step 21** — On failure:

If the MCP tool call returns an error:

| Error type | Action |
|---|---|
| Insufficient buying power | Show current buying power, suggest reducing quantity or using a limit order |
| Invalid symbol | Verify the symbol with the asset lookup tool (`get_asset` as of v2), suggest corrections |
| Invalid parameters | Show the parameter that failed validation, reference the correct schema |
| Market closed (for `day` TIF) | Show market hours via the clock tool, suggest `gtc` or waiting for open |
| Options not enabled | Tell you to enable options trading in Alpaca dashboard |
| Account restricted | Show the restriction reason, suggest contacting Alpaca support |
| MCP tool error | Show the raw error, suggest checking MCP server logs |

Log the failed attempt in `order_log.csv` with status `FAILED` and the error message.

### Phase 6: Post-Submission Monitoring via MCP

**Step 22** — Check order status.

Call the single-order lookup tool — `get_order_by_id` as of v2 — with the order ID from Step 20. If the submission outcome was ambiguous and you have no order ID, look the order up by your idempotency key instead, using `get_order_by_client_id`.

Report the current status and any fill information.

**Step 23** — List all open orders (if requested or useful context).

Call the order-list tool — `get_orders` as of v2 — filtered to open orders.

Show a summary table of all open orders.

**Step 24** — Return order summary:

```
┌─────────────────────────────────────────┐
│           ORDER SUBMITTED               │
├─────────────────────┬───────────────────┤
│ Order ID            │ abc-123-def       │
│ Symbol              │ AAPL              │
│ Side                │ BUY               │
│ Qty                 │ 10                │
│ Type                │ LIMIT @ $185.50   │
│ Status              │ NEW               │
│ Submitted           │ 2026-07-26 15:30  │
│ Environment         │ PAPER (verified)  │
├─────────────────────┴───────────────────┤
│ Next: Check status, modify, or cancel.  │
└─────────────────────────────────────────┘
```

**Step 25** — Order lifecycle reporting.

As the order progresses, your agent reports state transitions:

| Status | Report to you |
|---|---|
| `new` / `accepted` | Order is live, waiting for fill |
| `partially_filled` | Show filled qty, remaining qty, avg fill price |
| `filled` | Show total filled qty, avg fill price, estimated cost |
| `canceled` | Confirm cancellation, show any filled portion |
| `expired` | Note expiration (TIF elapsed), suggest resubmission if appropriate |
| `rejected` | Show rejection reason, suggest remediation |
| `replaced` | Show old → new order details |

For filled or partially filled orders, calculate portfolio impact:
- New position size (or change to existing position)
- Estimated cost basis
- Remaining buying power
- Portfolio weight of this position

### Phase 7: Portfolio Impact via MCP

**Step 26** — Fetch all positions.

Call the all-positions tool — `get_all_positions` as of v2.

Show a positions summary table.

**Step 27** — Fetch a specific position (if checking a single symbol).

Call the single-position tool — `get_open_position` as of v2 — for the symbol in question.

Show position details: qty, avg entry, current price, unrealized P&L, market value.

**Step 28** — Fetch updated account.

Call the account-info tool again — `get_account_info` as of v2.

Show updated equity, buying power, and cash after the trade.

**Step 29** — Portfolio risk summary:

```
┌─────────────────────────────────────────────┐
│         Portfolio Risk Summary              │
├──────────────────┬──────────────────────────┤
│ Total Equity     │ $99,850.00              │
│ Cash             │ $98,000.00              │
│ Market Value     │ $1,855.00               │
│ Buying Power     │ $196,000.00             │
│ Positions        │ 1                       │
│ Largest Position │ AAPL (100% of invested) │
│ Unrealized P&L   │ +$5.00 (+0.27%)         │
│ Day P&L          │ +$5.00                  │
└──────────────────┴──────────────────────────┘
```

### Phase 8: Order Management via MCP

**Step 30** — Cancel a specific order.

Call the single-order cancel tool — `cancel_order_by_id` as of v2 — with the order ID.

Confirm cancellation. Note: filled orders cannot be canceled.

**Step 31** — Cancel all open orders.

Call the bulk cancel tool — `cancel_all_orders` as of v2. This acts on every open order in the account at once, so show the list it will affect and get confirmation before calling it, even when confirmation mode is OFF.

Confirm how many orders were canceled. Show any that could not be canceled (already filled/filling).

**Step 32** — Replace (modify) an existing order.

Call the replace tool — `replace_order_by_id` as of v2 — with the order ID and only the fields being changed.

Show the old → new comparison table. Only unfilled or partially-filled orders can be replaced.

**Step 33** — Close a single position.

Call the single-position close tool — `close_position` as of v2. It takes `symbol_or_asset_id` (required) and optionally either `qty` or `percentage`, which are mutually exclusive. Omitting both closes the entire position.

This is not a cancellation — it submits a market sell order for the position, so it moves real (paper) money and is subject to market hours. If the market is closed the order queues and executes at the next open, which means the fill price is unknown at the time you approve it. Your agent states this explicitly when the market is closed rather than implying the position is already flat.

Your agent shows the position it is about to close — symbol, quantity, market value, and unrealized P&L — and requires explicit confirmation. Confirmation mode governs order entry, and this is order entry, so an OFF setting does not skip the confirmation for a liquidation. After the call it reports the resulting order ID and monitors it to a terminal state exactly as it would any other order.

**Step 34** — Close all positions.

Call the bulk close tool — `close_all_positions` as of v2. Its one parameter, `cancel_orders`, cancels every open order before liquidating when set to `true`.

This is the most destructive operation in the skill: it liquidates the entire portfolio, including positions this session never opened, and with `cancel_orders: true` it destroys resting orders too. Your agent first shows the full inventory it will affect:

- Every open position, from the positions list tool, with symbol, quantity, market value, and unrealized P&L
- The total market value being liquidated
- Every open order that `cancel_orders: true` would cancel, if that flag is being set

It then states the count, and requires an explicit "yes" — always, regardless of `confirmation_mode`. Only then does it call the tool. Afterward it reports how many positions were closed and surfaces any that failed, since a partial failure leaves the portfolio in a half-liquidated state that you need to know about.

**Step 35** — Options exercise.

Exercising is irreversible and settles into the underlying, so `exercise_options_position` and `do_not_exercise_options_position` (as of v2) both carry the same explicit-confirmation requirement as Step 34. Your agent shows the contract, the resulting underlying obligation, and the cash impact before calling either one, and never issues an exercise instruction on its own initiative.

### Phase 9: Deployment Guidance (on request)

If you ask about automating these trades beyond interactive sessions:

**MCP-based automation**
- MCP servers are session-based and typically run within an agent host like Cursor
- For recurring MCP-based trades, explore Cursor automations or scheduled agent triggers
- The MCP server must be running and authenticated for each session

**Standalone automation**
- For production-grade automation, use the Alpaca SDK directly:
  - Python: `alpaca-py` (`pip install alpaca-py`)
  - TypeScript/JavaScript: `@alpacahq/alpaca-trade-api` or `@alpacahq/typescript-sdk`
- Cron + SDK script for scheduled strategies
- Cloud functions (AWS Lambda, GCP Cloud Functions) for event-driven trading
- Webhook-based triggers from TradingView or custom signal providers

Standalone automation leaves this skill's guarantees behind. The Step 12 paper gate covers MCP tool calls in an interactive session; an SDK script running under cron, a cloud function, or a webhook has no MCP server and no gate. The script must assert paper itself, at startup, and exit if it cannot — construct the client with `paper=True` as a literal rather than reading the endpoint from configuration, and abort if a live endpoint or live-trading flag is present in the environment. A live account returns the same response shape as a paper one, so nothing later in the run will surface the error.

**Always**:
- Validate any new automation against paper for a meaningful period before considering live at all
- Implement circuit breakers (max daily loss, max orders per day, max position size)
- Log all orders and monitor for unexpected behavior
- Your agent does not recommend specific cloud providers or infrastructure choices

---

## 5 — Execution rules

### Universal rules

1. **Paper only.** This skill is exclusively for paper trading. Your agent must verify the paper environment before every order submission.
2. **No financial advice.** Your agent executes trades at your direction. It does not recommend trades, predict prices, or suggest strategies.
3. **Confirmation by default.** Your agent asks for explicit confirmation before each order unless you opt out.
4. **Idempotency.** Every order gets a unique `client_order_id` to prevent duplicate submissions on retry.
5. **Complete transparency.** Every parameter sent to the MCP tool must be shown to you in the preview.
6. **Fail safe.** If any verification step fails (account check, paper verification, buying power), your agent stops and explains.
7. **No interpolation.** Your agent uses exactly the parameters you confirmed — never infers "you probably meant" and silently changes values.
8. **Disclose limitations.** If the MCP server does not support a requested feature (e.g., a specific order type), your agent tells you rather than attempting a workaround.
9. **Gate unscoped destructive tools.** `cancel_all_orders`, `close_all_positions`, `close_position`, `exercise_options_position`, and `do_not_exercise_options_position` act on holdings this session may never have created, and the last three are irreversible. Your agent lists exactly what each call will affect and requires explicit confirmation regardless of `confirmation_mode`, which governs order entry only.
10. **Closing a position is order entry.** The close tools submit market sell orders rather than deleting a position. They obey market hours, queue to the next open when the market is closed, and fill at an unknown price. Your agent monitors the resulting order to a terminal state instead of reporting the position as flat on the call returning.

### MCP-specific rules

11. **Always discover tools first.** Call `GetDynamicTools` to find the Alpaca namespace and inspect tool schemas before calling any tool. Tool names cited in this skill are current for v2 and are documentation, not a contract — v2 was a rewrite in which none of the v1 tools survived, and a name can persist across versions while its schema changes. Confirm against discovery and never hard-code a parameter schema.
12. **Handle namespace states.** If the MCP namespace is `"needsAuth"`, authenticate via `mcp_auth`. If `"error"` or not found, tell you to check the MCP server configuration.
13. **No raw HTTP fallback.** This is the MCP version — do not fall back to direct HTTP API calls or CLI commands if the MCP server is available and functioning. This governs how your agent reaches Alpaca. It does not forbid reading the local MCP config for the Step 12 paper gate, which touches no Alpaca endpoint.
14. **Auth errors are not retryable with different credentials.** If an MCP tool call fails with an authentication error, tell you to check the MCP server configuration. Do not retry with different credentials or attempt to pass API keys as tool arguments.
15. **MCP tool calls do not need `required_permissions: ["all"]`.** They run through the MCP protocol, not the shell.
16. **Respect MCP server boundaries.** If the discovered schema does not include a parameter you expect (e.g., `position_intent` for options), do not invent it — tell you and reference the API docs for workarounds.
17. **Re-discover on error.** If an MCP tool call fails with an unexpected schema error, re-discover tools with `GetDynamicTools` in case the server was updated.

### Asset-class-specific rules

18. **Equities** — Verify the symbol exists and is tradable via the asset lookup tool before ordering. Check for stock splits, halts, or delistings.
19. **Options** — Verify options approval level. Resolve the contract through the option contracts tool rather than trusting a hand-built OCC symbol (e.g., `AAPL251219C00250000`). Confirm `position_intent`.
20. **Crypto** — Use the slash-pair format (e.g., `BTC/USD`). Note 24/7 trading availability. Fractional quantities are common — confirm precision.

---

## 6 — Output contract

### Run folder structure

```
runs/<YYYYMMDD-HHMMSS>-paper-trading-mcp/
  notes.md              # Strategy description, assumptions, risk controls
  orders.json           # All MCP order responses (create, get, list)
  order_log.csv         # Chronological log of all order actions
  positions_snapshot.json  # Position state after trades
  portfolio_summary.md  # Account and portfolio state
  review.md             # Session review and lessons learned
```

### notes.md

Contains:
- Strategy description and rationale
- All confirmed parameters
- Risk controls in effect
- Paper environment verification details
- Any assumptions made
- Timestamps

### orders.json

Array of all order-related MCP responses captured during the session:

```json
[
  {
    "action": "create",
    "timestamp": "2026-07-26T19:30:00Z",
    "request": {
      "symbol": "AAPL",
      "side": "buy",
      "qty": "10",
      "type": "limit",
      "limit_price": "185.50",
      "time_in_force": "day"
    },
    "response": {
      "id": "abc-123-def",
      "status": "new",
      "filled_qty": "0",
      "created_at": "2026-07-26T19:30:01Z"
    }
  }
]
```

### order_log.csv

```csv
timestamp,action,order_id,client_order_id,symbol,side,qty,type,limit_price,stop_price,tif,status,filled_qty,filled_avg_price,error
2026-07-26T19:30:00Z,CREATE,abc-123-def,pt-20260726-001,AAPL,buy,10,limit,185.50,,day,new,0,,
2026-07-26T19:31:00Z,STATUS,abc-123-def,pt-20260726-001,AAPL,buy,10,limit,185.50,,day,filled,10,185.48,
```

### positions_snapshot.json

Captured from the list-positions MCP response after all trades are complete.

### portfolio_summary.md

Human-readable summary of account state, positions, and risk metrics after the session.

### review.md

Post-session review: what was traded, outcomes, lessons, what to do next.

> **Note**: Unlike CLI output, MCP responses are not automatically saved as raw files. Your agent must capture relevant response data and write it to `orders.json` and `order_log.csv` explicitly.

---

## 7 — Validation and tests

### Pre-submission checks

Your agent validates before every order submission:

| Check | How | Fail action |
|---|---|---|
| Paper environment | `env.ALPACA_PAPER_TRADE` in the host's MCP config is absent, `true`, `1`, or `yes`. Not readable from any tool — read the config file. Fail closed if unreadable | STOP — tell you to reconfigure |
| Account active | `status == "ACTIVE"` | STOP — account issue |
| Trading not blocked | `trading_blocked == false` | STOP — account restricted |
| Sufficient buying power | `buying_power >= est_notional` | STOP — show buying power, suggest smaller order |
| Symbol tradable | Get-asset tool | STOP — symbol not found or not tradable |
| Options approved | Account options level | STOP — tell you to enable options |
| Crypto enabled | Account crypto status | STOP — tell you to enable crypto |
| Valid order type | Schema validation | STOP — show valid order types |
| Valid TIF | Schema validation | STOP — show valid TIF options |
| Price levels present | Limit/stop price for limit/stop orders | STOP — ask for missing price |
| Client order ID | UUID generated | Generate if missing |

### Post-submission checks

| Check | How | Fail action |
|---|---|---|
| Order accepted | Response status | Report rejection reason |
| No duplicate | client_order_id uniqueness | Warn if duplicate detected |
| Fill within expectations | filled_avg_price vs limit_price | Alert if unexpected |

### MCP-specific validation tests

Validate these MCP-specific failure modes:
- MCP namespace not found
- MCP namespace needs authentication
- MCP tool schema changes
- MCP server configured for live environment
- MCP tool call network errors

---

## 8 — Disclosures, safety, and data handling

### Disclosures

Your agent must include these disclosures:

- **Before every order preview:**
  > "Paper trading only. Not financial advice. Past performance does not guarantee future results."

- **If discussing strategy performance:**
  > "Paper trading results are simulated and may not reflect real-world execution, slippage, or market impact."

- **If discussing options:**
  > "Options involve significant risk and are not suitable for all investors. Paper trading options does not carry financial risk, but the strategies tested may involve substantial risk if applied to live trading."

- **Full disclosures.** Review Alpaca's disclosures and agreements at [alpaca.markets/disclosures](https://alpaca.markets/disclosures).

> **Important disclosure:** This material is for informational, educational, and research purposes only. It is not investment advice, a recommendation, an offer, or a solicitation to buy or sell securities, options, cryptocurrencies, or any other financial product. All investing and trading involve risk, including possible loss of principal. Paper trading is simulated and may differ from live trading in fills, market impact, liquidity, fees, latency, and other factors. Review Alpaca's disclosures at https://alpaca.markets/disclosures.

### Safety

- **Never place live trades.** This skill checks for paper environment, but the MCP server configuration is ultimately your responsibility.
- **Never expose API keys.** Keys are configured in the MCP server environment, not passed through the agent.
- **Never provide financial advice.** Your agent executes orders at your direction and reports facts. It does not recommend trades.
- **Circuit breaker awareness.** If you submit many rapid orders, your agent should note the pace and ask if it is intentional.
- **Destructive tools are gated independently of confirmation mode.** Turning per-order confirmation OFF speeds up order entry. It never waives the explicit "yes" required for `close_all_positions`, `cancel_all_orders`, `close_position`, or an options exercise instruction.
- **The default toolset is the full toolset.** `ALPACA_TOOLSETS` defaults to all capabilities, so liquidation and exercise tools are reachable in any default install. Scope the variable if you want them out of the agent's reach entirely rather than relying on the gate alone.

### Data handling

- MCP tool calls go through the MCP protocol to the Alpaca API. Credentials live in the server's configuration and are never passed as tool arguments, so tool calls never place them in your agent's context.
- The one point where your agent touches the file holding those credentials is the Step 12 paper gate. It reads a single field from that file and must never read, print, or echo the file or the server entry as a whole. If your agent cannot extract just that field, it fails the gate rather than falling back to a wholesale read.
- Order data is saved locally in the run folder structure (see §6).
- No trading data is sent to third-party services beyond Alpaca.
- Your agent's conversation context may include order details — treat chat history accordingly.

---

## 9 — Anti-patterns

- **NEVER** call a tool named in this skill without confirming it against discovery — the names are documented for v2, not guaranteed.
- **NEVER** call MCP tools without first inspecting their schema via `GetDynamicTools`.
- **NEVER** assume the MCP server is configured for paper, and never treat an account response as proof of it — paper mode comes from `ALPACA_PAPER_TRADE`.
- **NEVER** read the MCP config file wholesale to check that flag — the same `env` block holds the API keys. Extract the single field.
- **NEVER** treat an unidentifiable server entry as an absent flag — absent passes, inconclusive fails closed.
- **NEVER** fall back to direct HTTP calls if the MCP server is available. This is the MCP version.
- **NEVER** pass API keys as MCP tool arguments — the server handles auth internally.
- **NEVER** place live trades or continue if the account appears to be live.
- **NEVER** submit an order without showing you a preview first.
- **NEVER** skip the paper-environment verification step.
- **NEVER** provide financial advice, price predictions, or trade recommendations.
- **NEVER** retry auth errors with different credentials — tell you to fix the MCP server config.
- **NEVER** silently change order parameters after your confirmation.
- **NEVER** assume a specific MCP server package name or version — discover at runtime.
- **NEVER** use `required_permissions: ["all"]` for MCP tool calls — they do not need it.
- **NEVER** invent MCP tool parameters not present in the discovered schema.
- **NEVER** treat partial fills as complete — always report remaining quantity.
- **NEVER** call `close_all_positions` or `cancel_all_orders` unprompted — both are unscoped and hit holdings this session never created. List what will be affected and require an explicit "yes".
- **NEVER** exercise an option without explicit confirmation — exercise and do-not-exercise instructions are irreversible.
- **NEVER** report a closed position as flat the moment the close tool returns — it submits a sell order that may still be queued or partially filled.

---

## 10 — Related files

- `reference.md` — MCP tool discovery patterns, order type reference, error handling, asset class specifics

### Companion skills

- `alpaca-trading-paper-trading` — Generic implementation-agnostic paper-trading skill
- `alpaca-trading-paper-trading-cli` — CLI-specific paper-trading skill
