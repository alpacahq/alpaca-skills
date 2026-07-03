# Decision Audit Trail - Reference

Companion to [SKILL.md](SKILL.md). Read the workflow and guardrails there first. The mechanism is
the open-source [`autonomous-audit`](https://pypi.org/project/autonomous-audit/) tool (Apache-2.0,
Python standard library only).

## CLI commands

```text
uvx autonomous-audit demo [DIR]              write + verify + report a sample chain
uvx autonomous-audit verify PATH             full-chain integrity check (exit 0 intact / 1 problem)
uvx autonomous-audit report PATH [-o OUT]    render an HTML decision report (stdout when no -o)
```

`verify` returns non-zero for a broken chain **and** for a missing file, invalid JSON, or an empty
log - a non-zero exit is not always "tampered". Read the printed message.

## Python API

```python
from autonomous_audit import AuditChainWriter, verify_chain

log = AuditChainWriter("decisions.jsonl")     # resumes an existing chain; a restart never forks it
log.append({...})                              # stamps prev_hash + hash, appends one JSON line
ok, err = verify_chain("decisions.jsonl")      # (True, None) if intact, else (False, "line N: ...")
```

- `AuditChainWriter(path, genesis_hash="0"*64, min_free_bytes=100*1024*1024)` - `append(record)`
  raises `AuditDiskFullError` when free disk is below the guard (it never silently drops a record).
- I/O is synchronous, blocking standard-library I/O. Inside an event loop, run `append` in a thread
  (e.g. `await loop.run_in_executor(None, log.append, record)`) so audit I/O never blocks the order
  path. It targets per-decision logging, not high-frequency streaming.

## Record schema

A record is any JSON-serialisable dict. The writer adds two fields:

| field | meaning |
| --- | --- |
| `prev_hash` | hash of the previous entry (genesis `"0"*64` for the first record) |
| `hash` | `SHA-256(canonical_preimage(entry))`, added after hashing |

Suggested fields for an Alpaca trading agent (illustrative, not required):

| field | example | note |
| --- | --- | --- |
| `timestamp` | `"2026-07-03T14:30:00+00:00"` | ISO 8601 |
| `symbol` | `"AAPL"` | the instrument |
| `side` | `"buy"` / `"sell"` | mirrors the Alpaca order intent |
| `qty` | `"10"` | string-typed for cross-language parity |
| `reason` | `"20-day breakout; risk gate passed"` | why the agent decided this |
| `alpaca_order_id` | `""` | link to the submitted order, if any |

Keep values **string-typed** for cross-language verification (see the hash contract below).

## Canonical hash contract (cross-language parity)

The pre-image hashed for an entry is:

```text
json.dumps(<entry without the "hash" field, prev_hash included>, sort_keys=True)
```

with Python's `json.dumps` defaults: `ensure_ascii=True` (non-ASCII characters are emitted as JSON
`\u` escape sequences) and `", "` / `": "` separators. Any other-language verifier must reproduce
this **byte-for-byte** - a naive `JSON.stringify` does not match (`ensure_ascii`, separators, and
float representation all differ; a Python-emulating serializer is required). This is why records
should stay **float-free** (use strings).

## Integrity scope

Detects **in-place edits, mid-chain deletions, and reorders** (each breaks the `prev_hash` linkage
or the recomputed hash). It does **not** by itself detect **truncation of the newest records** or a
**wholesale rewrite from genesis** - the chain has no anchored head or length commitment. If you
need that, publish/sign the current chain head externally.

Tamper-**evident**, not tamper-**proof**: a local file is inherently mutable; the chain lets you
*detect* alteration, not prevent it, and it does not on its own satisfy statutory record-keeping.

## Disclosure

Insights from this skill and connected AI agents are for educational and informational purposes
only and are not investment advice, a recommendation, or a solicitation. Chain integrity is not a
regulatory approval and is not model explainability. Trading involves risk; past results do not
guarantee future results. See [Alpaca disclosures](https://alpaca.markets/disclosures).
`autonomous-audit` is independent third-party open-source software, not an Alpaca product.
