---
name: alpaca-trading-backtest
description: >
  Execute deterministic, reproducible historical backtests from a start date,
  end date, and strategy concept using the Alpaca CLI plus agent-written
  workspace code. Use when the user wants to backtest a strategy, simulate
  historical trades, or return trades, diagnostics, and reproducibility artifacts.
---

# Trading API Backtesting

```text
strategy idea -> formalized rules -> confirmed assumptions -> CLI data fetch -> local script -> artifacts -> report
```

This is a reproducible research workflow, not a guarantee of live-market performance.

## Required disclosures

Every report, `notes.md`, `report.md`, notebook, or exported result must include:

> **Important disclosure**  
> This backtest is a hypothetical historical simulation and does not represent actual trading performance. Backtested results do not guarantee future results. Results depend on market-data quality, data feed selection, corporate-action handling, fees, slippage, liquidity, taxes, execution assumptions, and implementation details. This material is for research and educational purposes only and is not investment advice, a recommendation, an offer, or a solicitation to buy or sell securities, options, cryptocurrencies, or any other financial product. All investments involve risk and may lose value. Review Alpaca's disclosures at [alpaca.markets/disclosures](https://alpaca.markets/disclosures).

When paper trading appears, add:

> Paper trading is a simulated environment. It does not involve real money or actual securities transactions. Paper results may differ from live trading because of fill assumptions, market impact, liquidity, latency, data differences, order handling, fees, and other market conditions.

When modeling Alpaca securities trading-activity fees, link to `https://files.alpaca.markets/disclosures/library/BrokFeeSched.pdf` and record the PDF revision date, extraction timestamp, and modeled/excluded fee categories in `fee_source.json`.

## CLI prerequisites

Install the Alpaca CLI:

```bash
go install github.com/alpacahq/cli/cmd/alpaca@latest
# or: brew install alpacahq/tap/cli
```

Authenticate and verify before every run:

```bash
alpaca doctor
# if auth fails: alpaca profile login --api-key
# or set ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables
```

Never print or commit the secret key. Use `--quiet` for machine-readable output. Prefer current `--help` and `--schema` output over stale examples in this document, as the CLI evolves.

See [reference.md](reference.md) for full CLI data-fetch commands, pagination, and schema flags.

## Required workflow

1. Gather required inputs: start date, end date, strategy concept or file.
2. Infer the rest: asset class, symbols, timeframe, initial cash, position sizing, feed, adjustment, execution assumptions, benchmark.
3. Resolve [run considerations](#run-considerations-checklist): order simulation, indicators, dividends, splits, fees, slippage, calendar, look-ahead bias.
4. Translate freeform ideas into precise mathematical rules.
5. Present the formalized interpretation before writing code unless the request was already precise.
6. Check the workspace for reusable data, prior runs, and existing utilities.
7. Create a self-contained run folder.
8. Write `notes.md`, `strategy_spec.json`, `config.json`, and a readable run-specific script.
9. Fetch historical data via the CLI, save raw outputs, filter to market hours, compute data fingerprints.
10. Run the local simulation, write artifacts, and return the [Teaching Five](#in-chat-response-standard).

## Workspace awareness

Before generating new code or fetching data, inspect the workspace.

**Data reuse**: reuse raw/normalized files only when all fingerprint fields match — symbol, feed, adjustment, timeframe, calendar filter, and date range. If fingerprints differ, treat the data as different.

**Run lineage**: if this run is a variant of a prior run, `notes.md` must state what changed (e.g., changed RSI threshold, extended date range, changed fill model).

**Existing code**: reuse a workspace backtest engine only when it matches strategy requirements. Otherwise default to a single `run.py`.

## Run folder and artifact contract

```text
runs/YYYY-MM-DD_symbol_strategy_timeframe/
  notes.md
  strategy_spec.json
  config.json
  run.py
  requirements.txt or pyproject.toml (when needed)
  raw/
    bars_SYMBOL.json
    quotes_SYMBOL.json (when fetched)
    calendar.json
    corporate_actions.json (when fetched)
  normalized/
    bars_SYMBOL.csv
  summary.json
  report.md
  trades.csv
  round_trips.csv
  equity.csv
  benchmark_equity.csv
  data_fingerprint.json
  warnings.json
  fee_source.json
```

`notes.md` must include: original request, confirmed interpretation, every inferred assumption, indicator definitions, fill model, fee model, feed and adjustment mode, dividend/split treatment, benchmark definitions, calendar handling, warnings, caveats, and disclosure links.

See [reference.md](reference.md) for artifact JSON schemas.

## Code generation rules

Generate a single-file `run.py` by default. Use readable code:

```python
fill_price = bar_open * (1 + friction_pct)
```

Generated code must:
- read raw/normalized files from the run folder
- implement the confirmed strategy and indicator definitions exactly — see [talib.md](talib.md)
- keep signal timing separate from fill timing
- compute fees, slippage, spread, and settlement per confirmed assumptions
- produce all required artifacts with deterministic sorting and timezone handling
- avoid hidden network calls after data fetch

Use Python 3. Prefer standard library + pandas/numpy. When strategy needs technical indicators, prefer [talib](talib.md) for correctness and conciseness. Add dependencies only when they materially improve correctness or readability.

## Strategy translation

Before writing code, confirm every rule specifies: data field, trigger, inclusive/exclusive bounds, indicator variant and parameters, warmup behavior, position sizing, order type, fill model, and benchmark.

Example confirmation:

```text
I interpreted your strategy as:
- Symbol: SPY
- Timeframe: 1Day
- Data: Alpaca CLI bars, feed=sip, adjustment=split
- Indicator: SMA(50) and SMA(200), simple arithmetic mean of completed daily closes
- Entry: fast SMA crosses above slow SMA (next-bar open)
- Fill model: next_open bar proxy with 5 bps slippage
- Sizing: 100% of available cash, whole shares
- Benchmark: SPY buy-and-hold with same assumptions
```

## Fill models

Use these model names in confirmations and `notes.md`. Full implementation rules in [reference.md — Fill model rules](reference.md#fill-model-rules).

- **`next_open`** (default): signal on bar T close; fill on bar T+1 open.
- **`time_based`**: fill at a confirmed time of day; use quote bid/ask when available.
- **`same_bar`**: only when explicitly requested; document look-ahead risk in `notes.md`.
- **Limit/stop orders**: OHLC-bar eligibility rules apply; conservative intrabar conflict policy when stop and target both touch the same bar.

## Report format

`report.md` must lead with **Performance vs Benchmarks**:

```markdown
| | Total Return | Ann. Return | Max Drawdown | Sharpe | Final Equity |
|---|---:|---:|---:|---:|---:|
| **Strategy** | ...% | ...% | ...% | ... | $... |
| Benchmark | ...% | ...% | ...% | ... | $... |
```

Follow with: strategy configuration, symbols/timeframe/feed/adjustment, fill model and friction, first/last trade, detailed metrics, benchmark explanation, assumptions, data fingerprint, caveats, and the disclosure block. Metric definitions in [reference.md — Metric formulas](reference.md#metric-formulas).

## In-chat response standard

Lead with the **Teaching Five**:

1. Total return versus benchmark
2. Max drawdown
3. Number of trades
4. Win rate
5. Sharpe ratio versus benchmark

Then include: annualized return, profit factor, fees paid, first/last trade, assumptions made, data fingerprint summary, artifact paths, and most important caveats.

If no trades occurred, explain directly whether caused by warmup, no signal, insufficient cash, missing data, or calendar filtering.

## Run considerations checklist

Resolve each item before running:

- order simulation and fill timing
- quote-aware versus bar-proxy fills
- dividend and split/reverse-split handling
- execution friction (spread + slippage)
- PDF-derived trading-activity fees
- market hours and extended-hours inclusion
- calendar-based decisions
- benchmark choice
- look-ahead bias
- survivorship bias
- out-of-sample or walk-forward validation for parameter tuning
- overfitting risk for repeated variants

Document all choices not explicitly specified in `notes.md`.

## Safety and quality guardrails

Never:

- use future data in signal generation
- use `same_bar` model without documenting look-ahead risk
- hide execution assumptions
- mix adjusted bars with separate split adjustments
- pretend vague rules were fully specified
- include extended-hours bars unless explicitly requested
- silently substitute indicator variants or price fields (`open`/`close`/`high`/`low`/VWAP are not interchangeable)
- compute Sharpe from per-bar returns when daily Sharpe is reported
- use population std dev for Sharpe (use N-1)
- submit live orders as part of a historical backtest
- bypass the Alpaca CLI with direct HTTP calls
- run CLI commands in a sandbox without local auth and filesystem access
- generate a multi-module engine when a single-file script will do

## Related references

- [reference.md](reference.md) — CLI data acquisition, indicator formulas, fill model rules, metric formulas, benchmarks, artifact schemas
- [talib.md](talib.md) — using TA-Lib for technical indicators in backtest scripts
