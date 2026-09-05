---
name: alpaca-trading-signal-parity
description: >
  Guarantee that a strategy's backtest and its live or paper execution compute
  signals from the same code, and prove it with a gate that can fail. Use when a
  backtested strategy is about to be traded, when a backtest and a running
  strategy disagree, or when signal logic exists in more than one place.
---

# Trading API Signal Parity

Use this skill when a strategy is moving from research to execution, or is
already running in both places. A backtest earns trust by being reproducible.
That trust transfers to the account only if the code that produced the
backtested signals is the same code that produces the live ones. This skill
makes that sameness explicit, mechanical, and testable.

This skill does not backtest and does not place orders. It sits between
`alpaca-trading-backtest` and `alpaca-trading-paper-trading`, and it hardens the
seam those two share.

## Required disclosures

Every report, `notes.md`, `parity.md`, or exported result produced under this
skill should include:

> **Important disclosure**  
> This material is for research and educational purposes only and is not
> investment advice, a recommendation, an offer, or a solicitation to buy or
> sell securities, options, cryptocurrencies, or any other financial product.
> Signal parity establishes that two code paths agree with each other. It does
> not establish that the strategy is profitable, that historical results will
> repeat, or that live execution will match a simulation — fills, latency,
> liquidity, fees, market impact, and data-feed differences remain. All
> investments involve risk and may lose value. Review Alpaca's disclosures and
> agreements at [alpaca.markets/disclosures](https://alpaca.markets/disclosures).

When paper trading appears in the workflow, add:

> Paper trading is a simulated environment. It does not involve real money or
> actual securities transactions. Paper results may differ from live trading
> because of fill assumptions, market impact, liquidity, latency, data
> differences, order handling, fees, and other market conditions.

## The failure this prevents

Signal logic is written twice more often than anyone intends. The backtest is
written first, in a research script optimized for vectorized speed over a full
history. The executor is written second, weeks later, in a scheduled job that
sees one bar at a time. Both compute "RSI(14) ≤ 30". Neither imports the other.

They then drift, and every route is quiet:

- One uses Wilder's smoothing, the other a simple moving average. Both are
  called RSI. They cross the threshold on different days.
- The research script computes indicators over the full series; the executor
  warms up on a shorter window and reports a different value for the same bar.
- A threshold is tuned in the research script and never copied across.
- A TA library is upgraded. One path picks it up; the other has it pinned.
- The backtest reads adjusted bars; the executor reads raw. Every split silently
  becomes a signal difference.

None of these fail loudly. The backtest stays green, the job keeps running, the
account keeps trading — and the numbers that justified the strategy describe
code that is no longer the code placing orders. The strategy was never tested;
its twin was.

**The rule this skill enforces: one signal implementation, imported by both
paths, with a gate that fails when they diverge.**

## Prerequisites

- A strategy with at least one backtest run and one execution path (live, paper,
  or scheduled). If execution does not exist yet, apply this skill anyway —
  retrofitting parity is far more expensive than starting with it.
- A test runner that can fail a build (`pytest`, `node --test`, or equivalent).
- Alpaca credentials via environment variables (`ALPACA_API_KEY`,
  `ALPACA_SECRET_KEY`). Never hardcode keys, and never write them into artifacts.
- Historical bars for the parity fixture, via the Alpaca CLI or Market Data API.
  See [reference.md](reference.md) for the commands.

## Required workflow

Work through these in order. Do not skip step 6.

### 1. Inventory every place a signal is computed

Search the workspace for indicator names, threshold constants, and comparison
operators against them. List each hit with its file, and state plainly which
ones are reachable from the backtest and which from the executor. Report the
list before changing anything — the user usually does not know how many copies
exist.

### 2. Extract one pure signal module

Move signal computation into a single module with no I/O, no network calls, no
clock reads, and no credentials. It takes bars and parameters and returns
signals. Purity is not style here: an impure module cannot be given a fixed
input, and a module that cannot be given a fixed input cannot be compared
against itself.

```python
# signals.py — the only place a signal is decided
def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Wilder's RSI. Returns None for bars before the warm-up completes."""
    ...

def decide(bars: list[dict], params: dict) -> list[str]:
    """Return one of 'buy' | 'sell' | 'hold' per bar. No I/O, no clock."""
    ...
```

Keep the warm-up contract explicit: a bar that cannot yet be evaluated returns
`None`/`hold`, never a silently truncated series. Warm-up mismatches are the
most common cause of a parity failure, and the hardest to see.

### 3. Make both callers import it

The backtest runner and the executor both import `decide`. Neither reimplements
it, neither copies a threshold, neither "adjusts it slightly for live". If the
executor needs a single-bar interface, give the module one and have it call the
same core — do not fork the logic to get a different shape.

Delete the old implementations in the same change. A superseded copy left in the
tree is the next drift.

### 4. Fingerprint the module

Record a SHA-256 of the signal module's source in every backtest run folder, and
in whatever the executor writes as its own state or startup log.

```
signal_module_sha256: 9f2c...  # of signals.py
params_sha256:        4ab1...  # of the resolved parameter set
```

The fingerprint is what makes a report auditable after the fact. Without it,
"this backtest justified this position" is a claim about the past that nobody
can check.

### 5. Write the parity gate

Feed one fixed bar fixture through both paths and assert the signal sequences
are identical, element by element — not aggregate counts, not trade totals.
Aggregates hide offsetting differences.

The gate belongs in the test suite that already blocks the build. A gate in a
script someone remembers to run is not a gate.

```python
def test_backtest_and_executor_agree():
    bars = load_fixture("fixtures/parity_bars.json")   # committed, not fetched
    assert backtest_signals(bars) == [executor_signal(bars[:i + 1])
                                      for i in range(len(bars))]
```

Commit the fixture. A gate that fetches its own data fails on API outages, gives
different verdicts on different days, and cannot be trusted to mean what it said
yesterday.

### 6. Prove the gate can fail

**A parity gate that has never been red is not known to work.** Add a positive
control that injects a defect and asserts the gate catches it. At minimum:

- change a threshold in a copy of the params → gate red;
- shift the warm-up by one bar → gate red;
- swap Wilder's smoothing for a simple average → gate red;
- leave everything correct → gate green.

Run it and show the output. A green parity gate over a blind comparison is
indistinguishable from a green gate over a working one, and the blind version is
worse than nothing because it is trusted.

### 7. Block execution on fingerprint mismatch

At executor startup, compare the fingerprint of the loaded signal module against
the one recorded by the backtest that authorized the strategy. A mismatch is a
**hard block, not a warning** — the same posture `alpaca-trading-paper-trading`
takes toward live credentials.

Fail closed: if the fingerprint is missing, unreadable, or empty, block. A gate
that opens when it has nothing to say is the most dangerous kind, because it is
silent exactly when something is wrong.

## Artifact contract

Write a `parity/` folder alongside the backtest run folder:

```
parity/
  parity.md          # what was unified, what was deleted, what remains a caveat
  parity.json        # fingerprints, fixture hash, gate result, timestamp
  fixtures/
    parity_bars.json # the committed bar fixture the gate runs on
```

Schemas are in [reference.md](reference.md).

## Guardrails

1. **One implementation.** If an indicator exists in two files, parity is not
   achieved, however well the two agree today.
2. **No "backtest-only" variants.** A faster vectorized path is allowed only if
   it is the same module and the gate proves both shapes agree.
3. **Pin the indicator library.** An unpinned TA dependency makes the fingerprint
   a claim about your code and a lie about your signals. Record the resolved
   version next to the fingerprint.
4. **Same data contract on both sides.** Adjusted vs raw bars, feed selection,
   and session filtering are part of the signal. State them in `parity.md`, and
   pin them in the fixture.
5. **Element-wise assertions only.** Comparing trade counts or returns lets two
   different signal series pass.
6. **Fingerprint mismatch blocks; missing fingerprint blocks.**
7. **Never write credentials into `parity.json`, fixtures, or logs.**
8. **Parity is not profitability.** Say so in every report. Two paths agreeing
   proves they are the same strategy, not that the strategy works.

## In-chat response standard

Report, in this order:

1. How many signal implementations were found, and where.
2. What was unified and what was deleted.
3. The parity gate result, plus **the positive control output** proving it can
   fail. A parity claim without the red proof is incomplete.
4. Fingerprints and the pinned indicator-library version.
5. Remaining caveats — anything the gate does not cover (fills, latency,
   slippage, partial fills, market impact).
6. The required disclosure.

## Troubleshooting

**The gate is red and both paths look correct.** Print the first differing index
and the inputs around it. It is almost always warm-up: the executor has fewer
prior bars than the backtest had at the same timestamp.

**The gate goes green after a refactor that should have broken it.** The gate is
probably comparing a cached result, or the fixture is shorter than the warm-up
window and every entry is `hold`. Re-run the positive control.

**The executor needs data the pure module cannot fetch.** Correct — it should
not. Fetch outside, pass bars in. If a signal genuinely needs a second series,
make it a second argument, not a network call inside the module.

**Parity holds but live results still diverge from the backtest.** Expected, and
outside this skill's scope: parity covers signal generation only. Fills,
latency, slippage, fees, and liquidity live in the execution layer. Say this
explicitly rather than letting a green gate imply more than it proves.

## Related files

- [reference.md](reference.md)
