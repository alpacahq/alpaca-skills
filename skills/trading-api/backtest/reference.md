# Backtest Reference


## Supported asset classes

V1 supports one asset family per run:

- `stocks`
- `crypto`

Multiple symbols within the same family are fine. Mixed-family portfolios are out of scope unless the generated code explicitly models them.

## CLI data acquisition

### Discover current command flags

Before hard-coding command syntax, use:

```bash
alpaca data bars --help
alpaca data quotes --help
alpaca data trades --help
alpaca data corporate-actions --help
alpaca calendar --help
```

Use schema output to understand fields:

```bash
alpaca data bars --schema
alpaca data quotes --schema
alpaca data trades --schema
```

### Fetch bars for signals

Bars are the default input for indicators and signal rules:

```bash
alpaca data bars \
  --symbol SPY \
  --start 2020-01-01 \
  --end 2025-12-31 \
  --timeframe 1Day \
  --feed sip \
  --adjustment split \
  --quiet > raw/bars_SPY.json
```

For multiple symbols:

```bash
alpaca data multi-bars \
  --symbols SPY,QQQ,IWM \
  --start 2020-01-01 \
  --end 2025-12-31 \
  --timeframe 1Day \
  --feed sip \
  --adjustment split \
  --quiet > raw/bars_multi.json
```

### Fetch quotes for fills

Quotes improve fill modeling for intraday and marketable-order assumptions:

```bash
alpaca data quotes \
  --symbol SPY \
  --start 2025-01-02T09:30:00-05:00 \
  --end 2025-01-02T16:00:00-05:00 \
  --feed sip \
  --quiet > raw/quotes_SPY_2025-01-02.json
```

When quotes are unavailable or impractical for the timeframe, the report should say which bar proxy and friction model were used.

### Fetch trades when replay is needed

```bash
alpaca data trades \
  --symbol SPY \
  --start 2025-01-02T09:30:00-05:00 \
  --end 2025-01-02T16:00:00-05:00 \
  --feed sip \
  --quiet > raw/trades_SPY_2025-01-02.json
```

### Fetch calendar and clock

```bash
alpaca calendar --start 2025-01-01 --end 2025-12-31 --quiet > raw/calendar.json
alpaca clock --quiet > raw/clock.json
```

### Fetch corporate actions

```bash
alpaca data corporate-actions --help
alpaca data corporate-actions \
  --symbols SPY \
  --start 2020-01-01 \
  --end 2025-12-31 \
  --quiet > raw/corporate_actions.json
```

### Pagination

If the response contains `next_page_token`, fetch all pages and record page count in the data fingerprint. Confirm the exact flag from `--help`; a typical pattern is:

```bash
alpaca data bars --symbol SPY --start 2025-01-01 --limit 500 --quiet > page1.json
alpaca data bars --symbol SPY --start 2025-01-01 --limit 500 --page-token TOKEN --quiet > page2.json
```

## CLI quick reference

### Connectivity check

```bash
alpaca doctor
```

### Historical bars

```bash
alpaca data bars --symbol AAPL --start 2025-01-01 --end 2025-12-31 --timeframe 1Day --csv
```

Key flags: `--symbol`, `--start`, `--end`, `--timeframe` (e.g. `1Min`, `5Min`, `15Min`, `1Hour`, `1Day`), `--feed` (default `sip`), `--adjustment` (default `raw`), `--limit` (default 1000 — paginate with `--page-token`).

Response fields: `t` (timestamp), `o` (open), `h` (high), `l` (low), `c` (close), `v` (volume), `n` (trade count), `vw` (VWAP).

### Historical quotes

```bash
alpaca data quotes --symbol AAPL --start 2025-01-02T14:30:00Z --end 2025-01-02T14:31:00Z --limit 5
```

Response fields: `t`, `bp` (bid price), `bs` (bid size), `ap` (ask price), `as` (ask size). Buy fills use `ap`; sell fills use `bp`.

### Market calendar

```bash
alpaca calendar --start 2025-01-01 --end 2025-12-31
```

Response fields: `date`, `open`, `close`, `session_open`, `session_close`, `settlement_date`.

### Output format flags

- `--quiet` / `ALPACA_QUIET=1` — machine-readable JSON for parsing
- `--csv` — CSV output
- `--jq '<expr>'` — filter JSON
- `--schema` — response field names without fetching data

### Discovery

```bash
alpaca --help
alpaca data --help
alpaca data <cmd> --help
```

## Indicator formulas

See [talib.md](talib.md) for canonical indicator implementations and usage. Use talib by default; fall back to manual implementations only when the environment cannot install the TA-Lib C library or the strategy requires a non-standard variant.

## Fill model rules

**Signals vs fills**: Bars drive signal logic. Quote data drives fill prices when available. Always attempt to fetch historical quotes for fill timestamps.

### Quote-based fills (preferred)

- **Buy fill price** = `ask_price * (1 + slippage_pct)` where `slippage_pct = slippage_bps / 10000`.
- **Sell fill price** = `bid_price * (1 - slippage_pct)`.

The bid-ask spread replaces the `spread_bps` assumption. Only `slippage_bps` (market impact beyond the quoted spread) is added.

If the quote at the exact timestamp is missing, use the most recent quote before that timestamp. Document gaps in `notes.md`.

### Bar-based fills (fallback)

- **Buy** = `bar_price * (1 + friction_pct)` where `friction_pct = (spread_bps + slippage_bps) / 10000`.
- **Sell** = `bar_price * (1 - friction_pct)`.

Bar field by model: `next_open` → `open[t+1]`; `time_based` → open at target timestamp; `same_bar` → `close[t]`.

### Fill model timing

- **`next_open`**: signal on bar `t` close, fill at bar `t+1` open timestamp.
- **`time_based`**: fill at target timestamp; if no bar exists (early close, holiday), use nearest bar in session and document.
- **`same_bar`**: explicit request only; document look-ahead bias in `notes.md`.

### Stop orders

On bar `t`:

- Sell stop: if `low[t] <= stop_level`, fill at `min(open[t], stop_level)` plus sell friction.
- Buy stop: if `high[t] >= stop_level`, fill at `max(open[t], stop_level)` plus buy friction.

If the bar gaps through the stop, fill at the open.

### Limit orders

On bar `t`:

- Buy limit: if `low[t] <= limit_price`, fill at `min(open[t], limit_price)` plus buy friction.
- Sell limit: if `high[t] >= limit_price`, fill at `max(open[t], limit_price)` plus sell friction.

If stop and target both touch the same bar, use the configured intrabar conflict policy. Default: conservative.

### Position sizing

Calculate at **signal time** (bar `t` close), not fill time:

- `equity_fraction`: `shares = floor(equity * fraction / close[t])`
- `cash_fraction`: `shares = floor(cash * fraction / close[t])`
- `fixed_shares`: exact share count
- `fixed_notional`: `shares = floor(notional / close[t])`

Use whole shares (`floor`) unless you request fractional shares.

## Fee model

Model trading-activity fees from Alpaca's Brokerage Fee Schedule PDF when the strategy includes securities trading activity:

```text
https://files.alpaca.markets/disclosures/library/BrokFeeSched.pdf
```

Model applicable categories: SEC, FINRA TAF, FINRA CAT, ORF, OCC, ADR pass-through, commissions when applicable. Store source URL, revision date, extraction timestamp, and modeled categories in `fee_source.json`.

Reports should distinguish:

```text
execution friction: spread and slippage
trading-activity fees: PDF-derived regulatory/pass-through fees
commissions: if applicable
borrow or margin costs: if enabled
crypto costs: if crypto is tested
```

If a category is not modeled, report it as excluded.

## Metric formulas

Use a daily equity curve unless you confirm another cadence.

### Total return

```text
total_return = (final_equity / initial_cash) - 1
```

### Annualized return

```text
ann_return = (1 + total_return) ** (252 / trading_days) - 1
```

### Daily return

```text
daily_return[t] = (equity[t] / equity[t-1]) - 1
```

### Sharpe ratio

```text
Sharpe = mean(daily_returns) / sample_stddev(daily_returns) * sqrt(252)
```

- `sample_stddev` uses **N-1** denominator
- `risk_free_rate = 0` unless you override
- 252 trading days per year for US equities
- Compute from daily equity, not per-bar returns

### Max drawdown

```text
drawdown[t] = (equity[t] / running_max[t]) - 1
max_drawdown = min(drawdown)
```

### Hit rate

```text
hit_rate = winning_round_trips / total_round_trips
```

Winning round trip = positive net P&L after friction and modeled fees. Open positions at backtest end do not count.

### Profit factor

```text
profit_factor = sum(winning_pnl) / abs(sum(losing_pnl))
```

If no losing round trips, report `inf`. If no winning round trips, report `0`.

### Turnover

```text
turnover = total_notional_traded / mean(daily_equity)
```

`total_notional_traded` = sum of absolute notional value of all fills (buys + sells).

## Mandatory benchmarks

**Single-symbol strategy:**

```text
buy-and-hold of the same symbol
```

**Multi-symbol strategy:**

```text
buy-and-hold of each individual symbol at 100% allocation
equal-weight buy-and-hold of the same universe with no rebalancing
```

Benchmarks use the same execution assumptions, data feed, adjustment mode, and reporting cadence as the strategy.

## Artifact schemas

### `summary.json`

```json
{
  "strategy_name": "...",
  "start": "...",
  "end": "...",
  "symbols": ["..."],
  "timeframe": "1Day",
  "initial_cash": 100000,
  "metrics": {},
  "benchmarks": {},
  "first_trade": {},
  "last_trade": {},
  "assumptions": [],
  "warnings": [],
  "data_fingerprint": {},
  "fee_source": {},
  "artifacts": {}
}
```

### `data_fingerprint.json`

Per symbol:

```text
provider
access_method = alpaca_cli
feed
adjustment
timeframe
total_bars_fetched
bars_after_filter
first_bar_ts
last_bar_ts
close_sum
volume_sum
calendar_filter
raw_file_hash
normalized_file_hash
```

`close_sum` is a cheap equivalence check. File hashes are stronger.

Example embedded in `summary.json`:

```json
{
  "data_fingerprint": {
    "SPY": {
      "feed": "sip",
      "adjustment": "split",
      "timeframe": "1Day",
      "extended_hours": false,
      "total_bars_fetched": 0,
      "bars_after_filter": 0,
      "first_bar_ts": "...",
      "last_bar_ts": "...",
      "close_sum": 0.0
    }
  }
}
```

### `fee_source.json`

```json
{
  "url": "https://files.alpaca.markets/disclosures/library/BrokFeeSched.pdf",
  "revision_date": "...",
  "extracted_at": "...",
  "modeled_categories": [],
  "excluded_categories": []
}
```

### Output files

- `report.md` — human-readable summary; Performance vs Benchmarks table first
- `trades.csv` — executed fills
- `round_trips.csv` — realized entry/exit pairs
- `equity.csv` — daily equity, cash, exposure
- `benchmark_equity.csv` — benchmark equity series
- `warnings.json` — non-fatal issues encountered during the run
