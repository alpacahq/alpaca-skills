---
name: alpaca-trading-paper-trading-cli
description: >
  Preview, submit, inspect, and manage Alpaca paper-trading orders using the
  Alpaca CLI. Supports US equities, options, and crypto. Use this skill when
  you want your AI agent to take a strategy signal and execute it as a paper
  trade through the Alpaca command-line interface.
---

# Alpaca Paper Trading — CLI Version

Use this skill when you want your AI agent to preview, submit, inspect, and manage paper-trading orders using the Alpaca CLI.

This skill is written for you, a Trading API user working with your own Alpaca paper-trading account, CLI profile, and local workspace. Your agent executes all operations through the `alpaca` command-line tool, giving you full visibility into every command and its output.

This is the CLI-specific version. A generic (implementation-agnostic) version and an MCP-server version are also available as companion skills.

---

## 0 - How your AI agent should use this skill

1. **Start with the signal source.** Identify the origin of the trade idea — a backtest result, manual idea, scheduled trigger, or strategy output.
2. **Reiterate strategy logic and confirm with you.** Summarize the thesis, expected behavior, and conditions under which the order should execute. Wait for your confirmation before proceeding.
3. **Gather and confirm ALL configurations.** Timing, asset class, symbol, side, qty/notional, order type, TIF, limit/stop prices, extended-hours flag, risk controls, and margin usage — every parameter must be stated and confirmed.
4. **Confirm the CLI resolves to the paper endpoint.** Run `alpaca doctor` and require its `Trading:` line to read `https://paper-api.alpaca.markets`. If it shows the live endpoint, **STOP immediately** and alert you.
5. **Show a complete order preview** using a formatted table. Include the exact CLI command that will run.
6. **Ask whether you want explicit confirmation before each order** (default: ON). Respect your preference for the session.
7. **Submit via `alpaca order submit`** with the paper profile.
8. **Return order ID, status, submitted payload, and next inspection commands** so you can independently verify.
9. **Monitor order lifecycle** with `alpaca order get`. Report fills, rejections, cancellations with portfolio impact.
10. **Never place live trades.** Verify the resolved paper endpoint before every submission. If any ambiguity exists about the environment, STOP.

---

## 1 - Prerequisites

### Alpaca CLI installed and on PATH

```bash
alpaca version
```

Install if needed:

```bash
# Homebrew (macOS / Linux)
brew install alpacahq/tap/cli

# Or with Go — requires $GOPATH/bin (typically ~/go/bin) on your PATH
go install github.com/alpacahq/cli/cmd/alpaca@latest
```

> The CLI is in **Alpha Preview**. Commands, flags, and output formats may change between releases, which is why your agent discovers flags at runtime rather than trusting any list in this file.

### Paper profile configured

```bash
alpaca profile login
# or with API key
alpaca profile login --api-key
```

Discover login options:

```bash
alpaca profile login --help
```

### Connectivity verified

```bash
alpaca doctor
```

Your agent runs this before every trading session. If it fails, no orders are submitted.

### Asset-class requirements

| Asset class | Requirement |
|---|---|
| US equities | Paper account active |
| Options | Options trading enabled on paper account |
| Crypto | Crypto trading enabled on paper account |

### Environment

- A Go toolchain, only if installing via `go install`; the Homebrew formula ships a prebuilt binary and needs no Go
- `uuidgen` or equivalent (for client order IDs)

External `jq` is **not** required. The CLI ships a built-in `--jq` flag that filters its own JSON output.

---

## 2 - Gather inputs

Your agent collects the following before proceeding to order construction:

| Parameter | Description | Default | Required |
|---|---|---|---|
| `signal_source` | Origin of trade idea (backtest, manual, scheduled, strategy) | — | Yes |
| `symbol` | Ticker symbol (e.g., AAPL, BTC/USD, AAPL250718C00200000) | — | Yes |
| `asset_class` | `us_equity`, `us_option`, `crypto` | `us_equity` | Yes |
| `side` | `buy` or `sell` | — | Yes |
| `qty` | Number of shares/contracts/coins | — | Yes (or notional) |
| `notional` | Dollar amount (fractional shares). Market orders with `day` TIF only; cannot combine with `qty` | — | Yes (or qty) |
| `order_type` | `market`, `limit`, `stop`, `stop_limit`, `trailing_stop` — **supported values vary by asset class** | `market` | Yes |
| `time_in_force` | `day`, `gtc`, `ioc`, `fok`, `opg`, `cls` — **supported values vary by asset class** | `day` for equities and options; `gtc` for crypto | Yes |
| `order_class` | `simple`, `bracket`, `oco`, `oto` (equities); `simple`, `mleg` (options); `simple` (crypto) | `simple` | No |
| `limit_price` | Required for limit/stop_limit | — | Conditional |
| `stop_price` | Required for stop/stop_limit | — | Conditional |
| `trail_percent` | For trailing_stop | — | Conditional |
| `trail_price` | For trailing_stop | — | Conditional |
| `extended_hours` | Allow pre/post-market fills | `false` | No |
| `client_order_id` | Idempotency key, max 128 characters | Auto-generated by Alpaca if omitted | No |
| `profile` | Alpaca CLI profile name. Set it via the `ALPACA_PROFILE` environment variable for the whole session — **never** with the `-p`/`--profile` flag. See the warning in Step 10 | Currently active paper profile | No |
| `output_format` | JSON is the default; `--csv` for CSV, `--jq '<expr>'` to filter | JSON | No |
| `confirmation_mode` | Require explicit yes before each order | `ON` | No |
| `max_position_pct` | Max % of portfolio in single position | None | No |
| `max_order_value` | Hard cap on single order notional | None | No |

### Strategy confirmation checklist

Before building the order, your agent confirms:

- [ ] Strategy logic is clearly stated
- [ ] You understand what the order will do
- [ ] Entry criteria are met (if from backtest/signal)
- [ ] Exit criteria / stop-loss plan discussed
- [ ] Position sizing is intentional
- [ ] Risk controls reviewed

---

## 3 - Source-of-truth references

Your agent uses these authoritative sources for validation:

| Source | URL | Used for |
|---|---|---|
| Create an order | https://docs.alpaca.markets/us/reference/postorder | Order parameters, per-asset-class constraints, status codes |
| Alpaca CLI docs | https://docs.alpaca.markets/us/docs/alpacas-cli | CLI commands, flags, syntax |
| Order types | https://docs.alpaca.markets/us/docs/orders-at-alpaca | Order type behavior and requirements |
| Paper trading | https://docs.alpaca.markets/us/docs/paper-trading | Paper environment specifics |
| Options trading | https://docs.alpaca.markets/us/docs/options-trading | Options order requirements and approval levels |
| Crypto trading | https://docs.alpaca.markets/us/docs/crypto-trading | Crypto order specifics |
| Alpaca disclosures | https://alpaca.markets/disclosures | Disclosure language |

### CLI discovery rule

Your agent verifies flags at runtime rather than trusting this file:

```bash
alpaca --help-all              # full command tree with every flag
alpaca order submit --help     # flags for one command
alpaca order submit --schema   # response shape, without calling the API
```

The CLI is in Alpha Preview, so flags and output shapes can change between releases. Anything in this skill that contradicts `--help` output is stale; trust the CLI.

---

## 4 - Workflow

### Phase 1: Strategy Confirmation

**Step 1** — Identify the signal source.

Your agent asks: "Where does this trade idea come from?" Options include:
- A completed backtest (link to run folder if available)
- A manual trade idea you described
- A scheduled or recurring strategy trigger
- Output from another skill or system

**Step 2** — Reiterate the strategy logic.

Your agent summarizes:
- Thesis (why this trade)
- Expected outcome
- Time horizon
- Exit conditions or stop-loss plan

**Step 3** — Confirm interpretation.

Your agent asks: "Is this interpretation correct? Should I proceed to configure the order?"

---

### Phase 2: Configuration Agreement

**Step 4** — Confirm asset class and symbol.

Your agent validates the symbol format:
- Equities: `AAPL`, `MSFT`
- Options: OCC format `AAPL250718C00200000`
- Crypto: `BTC/USD`, `ETH/USD`

Format is necessary but not sufficient — a well-formed symbol can still be untradable or delisted. Your agent confirms it against the asset record:

```bash
alpaca asset get --symbol-or-asset-id AAPL
```

It requires `status` = `active` and `tradable` = `true`, and checks `fractionable` before proposing a notional or fractional-quantity order. For options, it resolves real contracts with `alpaca option contracts --underlying-symbols AAPL` rather than hand-assembling an OCC string.

**Step 5** — Confirm side, quantity, and order type.

**Step 6** — Confirm time-in-force and pricing parameters.

Time-in-force is not uniform across asset classes. Your agent validates the combination before building the command, because the API rejects the invalid ones:

| Asset class | Order types | Time-in-force | Order classes |
|---|---|---|---|
| US equities | `market`, `limit`, `stop`, `stop_limit`, `trailing_stop` | `day`, `gtc`, `opg`, `cls`, `ioc`, `fok` | `simple`, `bracket`, `oco`, `oto` |
| US options | `market`, `limit`, `stop`, `stop_limit` (`stop` types single-leg only) | `day`, `gtc` | `simple`, `mleg` |
| Crypto | `market`, `limit`, `stop_limit` | `gtc`, `ioc` — but `stop_limit` is `gtc`-only, and `ioc` applies only to `market` and `limit` | `simple` |

The CLI supplies the time-in-force default itself based on symbol shape: a symbol containing `/` (i.e. a crypto pair) defaults to `gtc`, everything else to `day`. Submitting a crypto order without `--time-in-force` therefore sends `gtc`, not `day`.

Alpaca's own sources disagree on the options row, so treat it as guidance rather than a hard gate. The OpenAPI spec's `TimeInForce`/`OrderType` descriptions say options are `market`/`limit` with `day` only; the Options Trading page and the Placing Orders matrix both allow `gtc` and both allow `stop`/`stop_limit` on single-leg orders. The two product pages agree with each other against the spec blob, so this table follows them. Your agent still defaults to `day` as the conservative choice and lets Alpaca reject rather than pre-blocking an order that the matrix permits.

Additional constraints that cut across order type:

- **Extended hours** requires `limit` type with `day` or `gtc` TIF. Every other type and TIF is rejected outright.
- **Trailing stop** accepts only `day` and `gtc`.
- **Notional** orders are market-type with `day` TIF only, cannot be combined with `qty`, and **cannot be replaced** — cancel and resubmit instead.
- **Bracket, OCO, and OTO** classes require `day` or `gtc`, do not support extended hours, and are equities-only.
- **Options** do not support extended hours at all. Multi-leg strategies use the `mleg` order class with up to 4 legs, and `stop`/`stop_limit` types are single-leg only.

**Step 7** — Confirm extended hours and client order ID preferences.

Alpaca supports three sessions outside regular hours, all of which require `extended_hours: true` on a limit order:

| Session | Window (ET) | Days |
|---|---|---|
| Overnight | 8:00pm – 4:00am | Sunday to Friday |
| Pre-market | 4:00am – 9:30am | Monday to Friday |
| After-hours | 4:00pm – 8:00pm | Monday to Friday |

Not every asset trades overnight; your agent confirms eligibility on the asset record rather than assuming.

**Step 8** — Review risk controls.

Your agent presents any position-sizing or max-value constraints and validates:
- Order notional vs. buying power
- New position concentration vs. portfolio
- Existing exposure to the same symbol

**Step 9** — Final configuration summary.

Your agent displays a complete parameter table and asks: "All parameters confirmed?"

---

### Phase 3: Paper Account Verification via CLI

**Step 10** — Confirm the CLI resolves to the paper endpoint:

```bash
alpaca doctor
```

`alpaca doctor` prints the fully-resolved trading endpoint under `Connectivity:`:

```
Connectivity:
  Trading:  https://paper-api.alpaca.markets
```

Your agent requires that line to read `https://paper-api.alpaca.markets`. The profile name is not a substitute. The CLI resolves paper vs. live in a fixed order — `ALPACA_LIVE_TRADE` first, then the active profile's `live_trade` field, then a paper default — so an exported `ALPACA_LIVE_TRADE=true` sends a profile named "paper" straight to the live endpoint. `alpaca doctor` reports the result of that whole chain.

> ⚠️ **`alpaca doctor` ignores the `-p`/`--profile` flag.** It accepts the flag and silently discards the value, always reporting the default profile. Every other command honors `-p`. So `alpaca doctor -p live` reports the *paper* endpoint while `alpaca order submit -p live` trades against the *live* one, and the guard passes while the order goes out live.
>
> Your agent therefore **never passes `-p`/`--profile` to any command.** To target a non-default profile it sets `ALPACA_PROFILE` once for the whole session, which `doctor` does honor, so the check and the order resolve identically. If any command in the session is about to receive `-p`, your agent stops instead.

If the `Trading:` line shows `https://api.alpaca.markets`, your agent **STOPS** immediately:

> ⚠️ LIVE ENDPOINT DETECTED. Your agent will not proceed. Unset `ALPACA_LIVE_TRADE` (or set it to `false`, which forces paper even on a live profile), select a paper profile with `alpaca profile switch <paper-profile-name>`, and restart.

**Step 11** — Confirm connectivity from the same `alpaca doctor` output.

Your agent confirms all checks pass. If any fail, it reports the failure and does not proceed. It does not re-run `alpaca doctor`; one invocation covers both this step and Step 10. `alpaca doctor` exits `0` when every check passes and `1` when any check fails.

**Step 12** — Fetch account status:

```bash
alpaca account get
```

Your agent parses and verifies:
- `status` = `ACTIVE`
- `account_blocked` = `false`
- `trading_blocked` = `false`
- `trade_suspended_by_user` = `false`
- `multiplier` — margin classification, and the only PDT signal the account object carries: `1` is a limited-margin cash-style account, `2` is a Reg T margin account, `4` is a PDT account with 4x intraday buying power

The Trading API account object has no `pattern_day_trader` or `daytrade_count` field. Your agent must not read them; infer PDT status from `multiplier` instead.

**Step 13** — Check buying power:

```bash
alpaca account get --jq '.buying_power'
```

Your agent compares estimated order value against available buying power. If insufficient, it warns you before proceeding.

**Step 14** — For options orders, check approval level:

```bash
alpaca account get --jq '{options_approved_level, options_trading_level, options_buying_power}'
```

Your agent gates on `options_trading_level`, which is the **effective** level — the minimum of `options_approved_level` and the `max_options_trading_level` in account configuration. Approval alone does not authorize trading if configuration caps it lower.

| Level | Permits |
|---|---|
| `0` | Options trading disabled |
| `1` | Covered calls, cash-secured puts |
| `2` | Long calls and puts (adds to level 1) |
| `3` | Spreads and straddles (adds to level 2) |

Spreads require level **3**, not level 2.

**Step 15** — Show account summary.

Your agent presents:

```
┌─────────────────────────────────────┐
│ Paper Account Summary               │
├─────────────────────────────────────┤
│ Endpoint:      paper-api (PAPER)    │
│ Profile:       my-paper             │
│ Status:        ACTIVE               │
│ Equity:        $50,000.00           │
│ Buying Power:  $100,000.00          │
│ Multiplier:    2 (Reg T margin)     │
│ Options Level: 2 (effective)        │
│ Crypto:        ACTIVE               │
└─────────────────────────────────────┘
```

---

### Phase 4: Order Preview

**Step 16** — Build the CLI command but DO NOT execute yet.

Your agent constructs the full command and displays it, then validates it with `--dry-run`, which prints the request body the CLI would send without submitting anything:

```bash
alpaca order submit \
  --symbol AAPL \
  --side buy \
  --qty 10 \
  --type limit \
  --limit-price 185.50 \
  --time-in-force day \
  --client-order-id a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  --dry-run
```

The command your agent shows you in the preview must be byte-identical to the one it later executes, minus `--dry-run`.

**Step 17** — Display formatted order preview table:

```
┌─────────────────────────────────────────────┐
│ ORDER PREVIEW — NOT YET SUBMITTED           │
├─────────────────────────────────────────────┤
│ Symbol:         AAPL                        │
│ Side:           BUY                         │
│ Quantity:       10 shares                   │
│ Order Type:     LIMIT                       │
│ Limit Price:    $185.50                     │
│ Time in Force:  DAY                         │
│ Extended Hours: No                          │
│ Est. Value:     $1,855.00                   │
│ Buying Power:   $100,000.00 → $98,145.00   │
│ Client ID:      a1b2c3d4-...               │
│ Endpoint:       paper-api (PAPER)           │
├─────────────────────────────────────────────┤
│ ⚠️  This is a PAPER trade — no real money   │
└─────────────────────────────────────────────┘
```

**Step 18** — If confirmation is ON: wait for explicit "yes" before proceeding.

**Step 19** — If confirmation is OFF: show the preview, then submit automatically.

---

### Phase 5: Order Submission

**Step 20** — Execute the CLI command:

```bash
CLIENT_ORDER_ID="$(uuidgen)"

alpaca order submit \
  --symbol AAPL \
  --side buy \
  --qty 10 \
  --type limit \
  --limit-price 185.50 \
  --time-in-force day \
  --client-order-id "$CLIENT_ORDER_ID"
```

Your agent captures `CLIENT_ORDER_ID` before submitting, so the order stays recoverable if the command dies before printing a response.

**Step 21** — Save raw CLI output to the run folder:

```bash
# Output saved to runs/<timestamp>-paper-trading-cli/raw/order_submit_response.json
```

**Step 22** — Parse response for key fields:
- `id` (order ID)
- `status` (expected: `new` or `accepted`)
- `created_at`
- `filled_at` (null for pending)
- `filled_qty`
- `filled_avg_price`

**Step 23** — On failure:
- Capture the structured JSON error from stderr and the CLI exit code — `0` success, `1` error, `2` auth failure
- Show remediation guidance (e.g., "insufficient buying power", "symbol not found", "market closed")
- Save error to `runs/<timestamp>/raw/error.json`
- Suggest corrective actions

If the failure is ambiguous — a timeout, a killed process, any case where your agent cannot tell whether the order reached Alpaca — it must **not** resubmit. It looks the order up by the client order ID it generated in Step 20:

```bash
alpaca order get-by-client-id --client-order-id "$CLIENT_ORDER_ID"
```

A hit means the order exists and resubmitting would duplicate it. Only a confirmed miss justifies a retry.

---

### Phase 6: Post-Submission Monitoring

**Step 24** — Check order status:

```bash
alpaca order get --order-id {order_id}
```

Your agent reports:
- Current status
- Fill progress (partial fills)
- Average fill price

**Step 25** — List recent orders for context:

```bash
alpaca order list --status open
```

**Step 26** — Return order summary to you:

```
┌─────────────────────────────────────────────┐
│ ORDER SUBMITTED ✓                           │
├─────────────────────────────────────────────┤
│ Order ID:      abc-123-def-456              │
│ Status:        NEW                          │
│ Symbol:        AAPL                         │
│ Side/Qty:      BUY 10                       │
│ Type:          LIMIT @ $185.50              │
│ Submitted:     2026-07-26T14:30:00Z         │
├─────────────────────────────────────────────┤
│ Next commands:                              │
│  alpaca order get --order-id abc-123      │
│  alpaca order cancel --order-id abc-123     │
│  alpaca position list                     │
└─────────────────────────────────────────────┘
```

**Step 27** — Order lifecycle updates:

| Event | Agent action |
|---|---|
| `filled` | Report fill price, calculate slippage vs. limit, show position impact |
| `partially_filled` | Report filled qty, remaining qty, average price |
| `rejected` | Surface rejection reason, suggest fix |
| `canceled` | Confirm cancellation, show final state |
| `expired` | Report expiration (TIF elapsed), suggest re-entry |
| `replaced` | Confirm replacement parameters, show new order ID |

---

### Phase 7: Portfolio Impact

**Step 28** — Fetch positions:

```bash
alpaca position list
```

Or for a specific symbol:

```bash
alpaca position get --symbol-or-asset-id AAPL
```

**Step 29** — Fetch updated account:

```bash
alpaca account get
```

**Step 30** — Show portfolio risk summary:

```
┌─────────────────────────────────────────────┐
│ PORTFOLIO IMPACT                            │
├─────────────────────────────────────────────┤
│ New Position:   AAPL — 10 shares @ $185.30  │
│ Position Value: $1,853.00                   │
│ Portfolio %:    0.74%                       │
│ Buying Power:   $98,147.00 (was $100,000)   │
│ Total Equity:   $250,000.00                 │
│ Open Orders:    1                           │
└─────────────────────────────────────────────┘
```

---

### Phase 8: Order Management

**Step 31** — Cancel a specific order:

```bash
alpaca order cancel --order-id {order_id}
```

Your agent confirms cancellation and reports final order state.

**Step 32** — Cancel all open orders.

`cancel-all` is unscoped: it cancels every open order on the account, including orders this session never created. The CLI executes it immediately with no confirmation prompt of its own, so your agent supplies the gate. It first shows exactly what will be destroyed:

```bash
alpaca order list --status open --jq '[.[] | {id, symbol, side, qty, type, limit_price}]'
```

Your agent lists those orders, states the count, and requires an explicit "yes" — even when `confirmation_mode` is OFF, since that setting governs order entry rather than mass cancellation. Only then:

```bash
alpaca order cancel-all
```

Your agent confirms total canceled and lists affected orders. The same gate applies to `alpaca position close-all`, which liquidates the entire portfolio.

**Step 33** — Replace an order (modify price/qty):

Discover available flags first:

```bash
alpaca order replace --help
```

Then execute:

```bash
alpaca order replace --order-id {order_id} --qty 5 --limit-price 186.00
```

Your agent reports the new order ID and updated parameters.

---

### Phase 9: Deployment Guidance (on request)

When you ask about automation, your agent provides guidance for:

**Bash script wrapper.** Unattended submission goes through a wrapper that proves the paper endpoint before it orders. Nothing scheduled calls `alpaca order submit` directly, so the guard cannot be bypassed by whichever scheduler invokes it:

```bash
#!/bin/bash
# /usr/local/bin/paper-trade.sh
set -euo pipefail

SYMBOL="${1:?usage: $0 SYMBOL SIDE QTY}"
SIDE="${2:?usage: $0 SYMBOL SIDE QTY}"
QTY="${3:?usage: $0 SYMBOL SIDE QTY}"

# Verify the CLI resolves to the paper endpoint
if ! alpaca doctor | grep -q 'Trading:.*https://paper-api\.alpaca\.markets'; then
  echo "ERROR: CLI is not pointed at the paper endpoint. Exiting." >&2
  exit 1
fi

alpaca order submit \
  --symbol "$SYMBOL" \
  --side "$SIDE" \
  --qty "$QTY" \
  --type market \
  --time-in-force day \
  --client-order-id "$(uuidgen)"
```

**Cron job.** Cron calls the wrapper, never the raw CLI:

```bash
# /etc/cron.d/paper-trade
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin
ALPACA_PROFILE=paper
0 9 * * 1-5 root /usr/local/bin/paper-trade.sh AAPL buy 1 >> /var/log/paper-trades.log 2>&1
```

Cron runs with a near-empty environment and does not source your shell profile, so `PATH`, `ALPACA_PROFILE`, and credentials must be set explicitly — in the crontab as above, or sourced inside the wrapper from a file readable only by the job's user. A scheduled job that inherits nothing is the case where an unguarded submit is most dangerous: there is no operator watching and no prompt, which is why the endpoint check belongs in the script rather than in the schedule.

**systemd timer / launchd plist:** Your agent generates the appropriate service file for your OS, pointing it at the same wrapper.

**CI/CD pipeline.** Install the CLI, authenticate from the runner's secret store, and invoke the same wrapper — never `alpaca order submit` as a bare step:

```yaml
- name: Submit paper order
  env:
    ALPACA_API_KEY: ${{ secrets.ALPACA_PAPER_API_KEY }}
    ALPACA_SECRET_KEY: ${{ secrets.ALPACA_PAPER_SECRET_KEY }}
    ALPACA_PROFILE: paper
  run: ./scripts/paper-trade.sh AAPL buy 1
```

CI is the easiest place to end up live by accident: the runner has no profile of yours, the keys come from whichever secret someone wired up, and a live key in a secret named for paper looks identical to a correct one at the call site. Naming the secret `PAPER` proves nothing, which is why the wrapper's `alpaca doctor` check — not the variable names — is what establishes the endpoint.

**Key automation notes:**
- The CLI never prompts. There are no "are you sure?" dialogs to suppress, in automation or interactively — which is exactly why the confirmation gates in this skill are the agent's responsibility, not the CLI's.
- `--quiet` suppresses warnings, hints, and color. It is not what makes output machine-readable; JSON is the default with or without it. Use it in cron and CI to keep logs clean.
- `ALPACA_OUTPUT=json|csv` sets the default output format for a whole script.
- Every unattended path — cron, systemd, launchd, CI — submits through the guarded wrapper. No scheduler or pipeline calls `alpaca order submit` directly, so the endpoint check cannot be skipped by adding a new trigger.
- Log all output for an audit trail.
- Use `--client-order-id` for idempotency in retry scenarios.

---

## 5 - Execution rules

### General rules

1. **Paper only.** Never submit orders against the live endpoint. Verify the resolved endpoint before every submission.
2. **Confirm before submit.** Default is explicit confirmation ON. Respect user preference.
3. **Preserve intent.** Never modify order parameters without your explicit agreement.
4. **Atomic operations.** Each order submission is independent. Failures don't affect other orders.
5. **Full transparency.** Show every CLI command before and after execution.
6. **Idempotency.** Always generate a `--client-order-id` to prevent duplicate submissions on retry.
7. **No financial advice.** Your agent executes your instructions. It does not recommend trades.

### CLI-specific rules

8. **Never pass `-p`/`--profile` to any command.** `alpaca doctor` ignores it, so the paper check and the order can resolve to different profiles. Use `ALPACA_PROFILE` for the session instead.
9. **Parse the default JSON output.** Every command returns structured JSON already. Use `--jq '<expr>'` to filter it and `--csv` only for human-facing tables. `--quiet` suppresses warnings, hints, and color; it does not change the data format.
10. **Never pipe to external `jq`.** The built-in `--jq` flag does the same job with one less dependency.
11. **Always discover flags with `--help`, `--help-all`, and `--schema` before assuming syntax.** The CLI is in Alpha Preview and may change between versions.
12. **Save all raw CLI output to the run folder.** Every command's stdout and stderr goes to `raw/`.
13. **If `alpaca doctor` fails, do not proceed.** Report the failure and stop.
14. **Redact profile details and tokens in summaries.** Never expose API keys or secrets in output files.
15. **Handle CLI exit codes.** `0` success, `1` error, `2` auth failure. Capture stderr and surface it.
16. **Do not add your own retry loop for rate limits.** The CLI already retries 429 and 5xx responses up to three times and respects `Retry-After`. A second backoff layer on top of it turns one rate-limited call into a much longer stall. If a command still fails after the CLI's retries, surface the error and stop.
17. **Preview with `--dry-run` before submitting.** It prints the exact request body without sending an order.
18. **Gate unscoped destructive commands.** `order cancel-all` and `position close-all` affect the whole account. Require explicit confirmation regardless of `confirmation_mode`.

---

## 6 - Output contract

Every paper-trading session produces a run folder:

```
runs/<YYYYMMDD-HHMMSS>-paper-trading-cli/
  notes.md                        # Session narrative: strategy, decisions, outcomes
  raw/                            # Saved raw CLI outputs
    account.json                  # Account state at session start
    order_submit_response.json    # Raw submission response
    order_status.json             # Order status checks
    positions.json                # Position state after fills
    clock.json                    # Market clock at submission time
    error.json                    # Error output (if any)
  orders.json                     # Structured order records
  order_log.csv                   # Tabular log: timestamp, action, order_id, status, details
  positions_snapshot.json         # Position state post-trade
  portfolio_summary.md            # Human-readable portfolio impact
  review.md                       # Session review: what worked, issues, next steps
```

### notes.md structure

```markdown
# Paper Trading Session — <timestamp>

## Signal Source
<origin of trade idea>

## Strategy
<strategy logic as confirmed>

## Orders Submitted
| # | Symbol | Side | Qty | Type | Status | Fill Price |
|---|--------|------|-----|------|--------|-----------|

## Portfolio Impact
<post-trade portfolio state>

## Issues / Notes
<any errors, warnings, or observations>
```

### order_log.csv columns

```
timestamp,action,order_id,symbol,side,qty,type,limit_price,stop_price,tif,status,fill_price,fill_qty,error
```

---

## 7 - Validation and tests

Your agent runs these checks during execution.

### Pre-submission validation

| Check | Command | Pass condition |
|---|---|---|
| CLI installed | `alpaca version` | Exit code 0 |
| Connectivity | `alpaca doctor` | All checks pass |
| Paper endpoint | `alpaca doctor` | `Trading:` line reads `https://paper-api.alpaca.markets` |
| Account active | `alpaca account get` | status=ACTIVE, not blocked |
| Buying power | `alpaca account get --jq '.buying_power'` | Sufficient for order |
| Market open | `alpaca clock` | `is_open=true` (unless extended hours or GTC) |
| Symbol valid and tradable | `alpaca asset get --symbol-or-asset-id X` | `status=active`, `tradable=true` |

### Post-submission validation

| Check | Command | Pass condition |
|---|---|---|
| Order accepted | `alpaca order get --order-id X` | Status != rejected |
| Fill received | Same | filled_qty > 0 |
| Position updated | `alpaca position get --symbol-or-asset-id X` | Reflects new position |

---

## 8 - Disclosures, safety, and data handling

### Disclosures

- **Paper trading only.** This skill operates exclusively in the Alpaca paper-trading environment. No real money is at risk.
- **Not financial advice.** Your agent executes your instructions. It does not provide investment recommendations, market predictions, or trading advice.
- **Paper ≠ live.** Paper fills may differ from live execution due to simplified fill simulation. Do not assume paper results predict live performance.
- **Your responsibility.** You are responsible for the strategies you choose to paper-trade. Your agent is a tool, not an advisor.
- **Full disclosures.** Review Alpaca's disclosures and agreements at [alpaca.markets/disclosures](https://alpaca.markets/disclosures).

> **Important disclosure:** This material is for informational, educational, and research purposes only. It is not investment advice, a recommendation, an offer, or a solicitation to buy or sell securities, options, cryptocurrencies, or any other financial product. All investing and trading involve risk, including possible loss of principal. Paper trading is simulated and may differ from live trading in fills, market impact, liquidity, fees, latency, and other factors. Review Alpaca's disclosures at https://alpaca.markets/disclosures.

### Safety controls

| Control | Implementation |
|---|---|
| Live-trade prevention | Resolved-endpoint check before every submission |
| Confirmation gate | Default ON — explicit yes required |
| Buying-power check | Pre-submission validation |
| Connectivity verification | `alpaca doctor` at session start |
| Error isolation | Failures logged, do not cascade |
| Idempotency | `--client-order-id` prevents duplicates |

### Data handling

- **Local only.** All run data stays in your local workspace under `runs/`.
- **No telemetry.** Your agent does not send trading data to external services beyond the Alpaca API.
- **Credential safety.** API keys are never logged, displayed, or written to files. Profile names are redacted in shared outputs.
- **Audit trail.** Every CLI command and response is saved in `raw/` for your review.

---

## 9 - Anti-patterns

Your agent must **NEVER**:

| Anti-pattern | Why | Correct approach |
|---|---|---|
| Submit against the live endpoint | Real money at risk | Always confirm `alpaca doctor` reports the paper endpoint first |
| Skip confirmation when mode is ON | You lose control | Always honor confirmation preference |
| Modify order params silently | Violates your intent | Re-confirm any parameter changes |
| Give trading advice | Liability, not agent's role | Execute instructions, don't recommend |
| Hard-code CLI flags | Alpha Preview — flags may change between versions | Discover with `--help`, `--help-all`, and `--schema` |
| Pipe output to external `jq` | Adds a dependency the CLI already provides | Use the built-in `--jq` flag |
| Treat `--quiet` as the JSON switch | JSON is the default; `--quiet` only drops warnings, hints, and color | Parse the default output directly |
| Read `pattern_day_trader` or `daytrade_count` | Neither field exists on the Trading API account object | Infer PDT from `multiplier` = `4` |
| Add a retry loop for 429s | The CLI already retries 3x and honors `Retry-After` | Surface the error after its retries fail |
| Run `cancel-all` or `close-all` unprompted | Unscoped — hits orders and positions this session never created | List what will be affected, require explicit confirmation |
| Bypass Alpaca CLI with direct HTTP calls | This is the CLI version | Use `alpaca` commands exclusively |
| Ignore CLI exit codes | Missed errors | Check exit code, capture stderr |
| Proceed after `alpaca doctor` fails | Connectivity not verified | Stop and report the failure |
| Store API keys in run folders | Security risk | Redact all credentials |
| Assume market hours | May be extended/crypto 24/7 | Check `alpaca clock` |
| Submit without buying-power check | Order will be rejected | Validate buying power first |
| Use `--csv` output for programmatic parsing | Less structured than JSON | Parse the default JSON, filtered with `--jq` |

---

## 10 - Related files

| File | Purpose |
|---|---|
| `reference.md` | Detailed reference: order types, TIF, lifecycle, asset classes, errors |

### Companion skills

| Skill | Description |
|---|---|
| `alpaca-trading-backtest` | Historical backtesting via Alpaca CLI — produces signals this skill can execute |
| `alpaca-trading-paper-trading` | Generic implementation-agnostic paper-trading skill |
| `alpaca-trading-paper-trading-mcp` | Trading API MCP version of this skill |
