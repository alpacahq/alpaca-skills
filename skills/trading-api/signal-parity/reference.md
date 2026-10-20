# Signal Parity Reference

Schemas, formulas, and commands for [SKILL.md](SKILL.md).

## Building the parity fixture

The fixture is a committed slice of historical bars that the gate replays on
every run. Choose a window that contains at least one of every signal the
strategy can emit, plus the full warm-up period before the first one.

```bash
# Daily bars for the fixture window (CSV, then convert to JSON in the workspace)
alpaca data bars --symbol AAPL --start 2025-01-01 --end 2025-06-30 \
  --timeframe 1Day --csv > fixtures/parity_bars.csv

# Confirm the CLI is authenticated and reachable before generating a fixture
alpaca version && alpaca doctor
```

Credentials come from `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in the
environment. Never inline them into commands, fixtures, or artifacts.

**Fixture rules**

| Rule | Why |
| --- | --- |
| Commit it | The gate must give the same verdict today and next quarter |
| Cover warm-up + first signal | A fixture shorter than the warm-up emits only `hold`, and passes blind |
| Record feed and adjustment | `sip`/`iex` and adjusted/raw are part of the signal, not transport |
| Hash it | A silently edited fixture turns a red gate green |

## `parity.json`

```json
{
  "schema": "alpaca-signal-parity/1",
  "generated_at": "2026-08-30T09:14:22Z",
  "signal_module": {
    "path": "signals.py",
    "sha256": "9f2c8a...",
    "pure": true
  },
  "params": {
    "resolved": { "rsi_period": 14, "entry_rsi_max": 30, "exit_rsi_min": 70 },
    "sha256": "4ab1d7..."
  },
  "indicator_library": { "name": "ta-lib", "version": "0.4.28", "pinned": true },
  "data_contract": {
    "feed": "sip",
    "adjustment": "split_and_dividend",
    "timeframe": "1Day",
    "session": "regular"
  },
  "fixture": { "path": "fixtures/parity_bars.json", "bars": 124, "sha256": "e30b91..." },
  "gate": {
    "result": "pass",
    "compared": "element-wise",
    "signals": 124,
    "first_divergence_index": null
  },
  "positive_control": {
    "run_at": "2026-08-30T09:14:25Z",
    "cases": 4,
    "red_as_expected": 3,
    "green_as_expected": 1
  },
  "callers": ["backtest/run.py", "executor/watch.py"]
}
```

`gate.result` may be `pass` or `fail`. `positive_control` is required: a
`parity.json` without it records an unproven gate, and should be treated as a
failed run.

## `parity.md` outline

1. Signal implementations found — file, reachable from which path
2. What was unified; what was deleted
3. Data contract on each side, and any difference that had to be reconciled
4. Gate result, element-wise, with the first divergence index if any
5. Positive-control table (below)
6. What parity does **not** cover — fills, latency, slippage, fees, liquidity
7. Required disclosure from [SKILL.md](SKILL.md)

## Positive-control matrix

The minimum set. Each row states the injected defect and the expected verdict.

| # | Injected defect | Expected |
| --- | --- | --- |
| 0 | none — healthy fixture and module | green |
| 1 | entry threshold changed in one path's params | red |
| 2 | warm-up shifted by one bar | red |
| 3 | Wilder's smoothing replaced with a simple average | red |
| 4 | adjusted bars on one side, raw on the other | red |
| 5 | fixture truncated below the warm-up window | red (or the gate is blind) |

Case 5 is the one most often missing. A fixture shorter than the warm-up makes
every signal `hold`, both paths agree trivially, and the gate reports success
while comparing nothing.

## Wilder's RSI

The definition mismatch behind most parity failures. Wilder's smoothing is not
a simple moving average, and both are called "RSI(14)".

```
change[i]  = close[i] - close[i-1]
gain[i]    = max(change[i], 0)
loss[i]    = max(-change[i], 0)

# Seed (first value at i = period):
avg_gain[period] = mean(gain[1..period])
avg_loss[period] = mean(loss[1..period])

# Wilder's smoothing thereafter:
avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i]) / period
avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i]) / period

rs[i]  = avg_gain[i] / avg_loss[i]        # avg_loss == 0 → RSI = 100
rsi[i] = 100 - (100 / (1 + rs[i]))
```

Bars before index `period` have no defined RSI. Return `None` for them; do not
seed with zeros and do not drop them silently — either choice shifts every
downstream index and produces exactly the off-by-one the gate exists to catch.

## Computing fingerprints

```bash
# Signal module
shasum -a 256 signals.py | cut -d' ' -f1

# Resolved parameters — canonicalize first, or key order becomes false drift
python3 -c "import json,hashlib,sys; \
print(hashlib.sha256(json.dumps(json.load(open('params.json')), sort_keys=True, \
separators=(',',':')).encode()).hexdigest())"
```

Canonicalization matters: serializing a dict without `sort_keys` makes an
unchanged parameter set produce a new hash whenever key order shifts, and a gate
that raises false alarms is switched off within a week.

## Related skills

| Skill | Relationship |
| --- | --- |
| `alpaca-trading-backtest` | Produces the run this skill fingerprints |
| `alpaca-trading-paper-trading` | The execution path that must import the same module |
| `alpaca-trading-paper-trading-cli` | Same, when execution is driven by the CLI |
