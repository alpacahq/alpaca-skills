---
name: alpaca-trading-decision-audit
description: >
  Record an AI trading agent's decisions (made against Alpaca's Trading API or CLI) to a
  tamper-evident SHA-256 hash-chain audit log, verify an existing log's integrity, and export a
  human-readable decision report. Use when the user wants an auditable, tamper-evident trail of
  what their agent decided, needs to check a decision log was not altered, or must produce a
  readable decision report. Read-only and offline - it never places orders.
---

# Trading API Decision Audit Trail

Give an Alpaca trading agent a **tamper-evident record of its own decisions**. As your agent
decides and (optionally) submits orders through Alpaca's Trading API or CLI, this skill appends
each decision to an append-only, SHA-256 hash-chained log; you can then **verify** the log was
not altered and **export** a readable report. It adds **integrity and traceability** to a
decision history - it does **not** place, modify, or cancel any orders.

The mechanism is the open-source [`autonomous-audit`](https://pypi.org/project/autonomous-audit/)
tool (Apache-2.0, Python standard library only), run via `uvx` - no account, keys, or network are
needed for the audit itself.

## Required disclosures

Every report or summary this skill produces must carry:

> **Disclosure.** This decision log is for educational and informational purposes only and is
> **not** investment advice, a recommendation, or a solicitation. It establishes
> **tamper-evidence** (integrity) of recorded decisions via a SHA-256 hash chain: it is
> **tamper-evident, not tamper-proof durable storage**, does not on its own satisfy statutory
> record-keeping, and is neither model explainability nor a regulatory approval. Trading involves
> risk; past results do not guarantee future results. See
> [Alpaca disclosures](https://alpaca.markets/disclosures). `autonomous-audit` is independent
> third-party open-source software, not an Alpaca product.

## Prerequisites

- **[`uv`](https://docs.astral.sh/uv/)** - runs the auditor with `uvx`, no install step:
  `uvx autonomous-audit demo` writes, verifies, and reports a sample chain.
- *(Context, optional)* the **[Alpaca CLI](https://github.com/alpacahq/cli)** / Trading API for
  the workflow whose decisions you are auditing. Authenticate with `alpaca profile login`, or set
  the `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` environment variables - **never** hard-code keys.

The auditor is **offline and read-only**: it needs no API keys, no network, and no broker
credentials. It only reads and writes the local decision-log file you point it at.

## What it does / does not

- **Does:** append decisions to a hash-chained log; detect in-place edits, reorders, and
  mid-chain deletions; export a self-contained HTML report.
- **Does not:** place, modify, or cancel orders; judge whether a decision was good; detect
  truncation of the newest records or a wholesale rewrite from genesis (anchor the chain head
  externally if you need that); provide explainability or satisfy regulatory retention.

## Workflow

### A. Record each decision

As your agent reaches a trading decision - from an Alpaca signal, an order it is about to submit
(`alpaca order submit ...`), or its own model - append one record. Mirror the Alpaca order intent
so the log lines up with what actually happened:

```python
from autonomous_audit import AuditChainWriter

log = AuditChainWriter("decisions.jsonl")
log.append({
    "timestamp": "2026-07-03T14:30:00+00:00",
    "symbol": "AAPL",
    "side": "buy",                 # decision, mirroring the Alpaca order intent
    "qty": "10",
    "reason": "20-day breakout; risk gate passed",
    "alpaca_order_id": "",         # fill in after submission, if you place the order
})
```

Keep values **string-typed** (float-free) if the log will also be verified outside Python.

### B. Verify integrity

```bash
uvx autonomous-audit verify decisions.jsonl   # exit 0 = intact; 1 = problem
```

On failure, state the failing line and whether it was a **hash mismatch** (an edited entry) or a
**`prev_hash` break** (a deleted or reordered entry).

### C. Export a report

```bash
uvx autonomous-audit report decisions.jsonl -o decision_report.html
```

Self-contained HTML: an integrity banner, one readable row per decision, and the disclosure.
Print it to PDF from any browser (no PDF dependency).

## Output contract

- `decisions.jsonl` - the append-only, hash-chained decision log (the source of truth).
- `decision_report.html` - the readable report; leads with the integrity result and ends with the
  disclosure.

Record schema and the canonical cross-language hash contract are in [reference.md](reference.md).

## In-chat response standard

When you verify or report, lead with:

1. integrity result (intact / broken, and where);
2. number of records;
3. the time span covered;
4. artifact paths (log + report).

Then include the disclosure, plus any caveats (e.g. records that were not float-free).

## Safety and quality guardrails

The agent must avoid:

- placing, modifying, or cancelling any Alpaca orders from this skill - it is read-only;
- editing the JSONL log by hand - it is append-only, and hand-edits break the chain;
- treating chain integrity as proof the **decisions** were correct, compliant, or profitable;
- committing API keys - use the `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` environment variables;
- writing floats into records that will be verified cross-language (use strings);
- deleting or truncating the log to "fix" a broken chain - investigate instead;
- exporting a report without the disclosure block;
- claiming regulatory approval or model explainability - integrity is neither.

## Troubleshooting

```text
verify reports "hash mismatch"
  An entry was edited after it was written. Restore the raw log; do not re-hash.

verify reports "prev_hash break"
  An entry was deleted or reordered. The chain is authoritative - find the missing entry.

AuditDiskFullError on append
  Free disk is below the guard (default 100 MB). Free space; the tool refuses to drop records.

hashes do not match a non-Python verifier
  A record contained a float. Re-record with string values (canonical parity requires it).
```

## Related files

- [reference.md](reference.md) - CLI, Python API, record schema, canonical hash contract.
