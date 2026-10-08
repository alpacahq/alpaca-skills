# Live-Readiness Review: Calibration Cases

These are **synthetic examples** for reviewer calibration, not executed tests, brokerage records, demonstrations of the current Alpaca API, or live-trading recommendations. Apply the status rules in [SKILL.md](SKILL.md). Real reviews require repository-specific evidence. Do not present these examples as proof of a real system's behavior.

A finding's status depends on the **quality and scope of the evidence**, not just how worrying the scenario sounds. The same subject can be `BLOCKED` if a failure path is observed or `NOT VERIFIED` if it has simply not been tested. Policy-dependent findings require an actual operator policy.

## Case 1: Long-side reward/risk inversion

**Declared design:** Enter long around $100; profit target $105; protective stop $97. No short position or closing-short order is involved.

**Observed evidence:** `strategy/order_plan.py:91` labels an order at $95 as `take_profit` for the long while the final intended position direction remains `long`; a unit test confirms the erroneous order plan is sent to the order builder. The test and file reference are illustrative.

**Finding:** `BLOCKED`. A supposed long take-profit below the entry contradicts the declared direction and may realize a loss. Distinguish the semantic trade intent and actual order side; the numeric relationship by itself is not a valid test for spread options or every order class.

**Resolution evidence:** Corrected order generation; direction-aware tests for long and short, plus opening/closing semantics; all alternate order paths checked.

## Case 2: Retry duplicates an uncertain order

**Observed evidence:** The submission wrapper creates a fresh `client_order_id` on every retry after a request timeout. It does not look up the original order or reconcile open orders before resubmission. A stateful fake returns timeout after accepting the first order; the retry yields two accepted buys.

**Finding:** `BLOCKED`. The implementation/test demonstrates a concrete duplicate-exposure path. Reusing an ID without broker-state reconciliation should not be declared sufficient in isolation.

**Resolution evidence:** Persisted original identifier, query/reconciliation path on ambiguous results, tests for accepted-but-timed-out, rejected, and transient unavailable outcomes, and no second placement before state is resolved.

## Case 3: An environment switch defaults to live

**Observed evidence:** A configuration function interprets an unset `TRADING_MODE` as `live`, and the startup path enables order submission without an explicit operator grant. A test confirms the unset-variable behavior; it does not make a real order.

**Finding:** `BLOCKED`. A missing configuration value can confer unintended live execution authority.

**Resolution evidence:** An explicit affirmative live-mode configuration and separate authorization; unknown mode fails closed; tests proving missing and invalid configurations cannot reach mutating endpoints. This review does **not** activate either environment.

## Case 4: Partial-fill handling is documented but untested

**Available evidence:** A paper-run summary shows ten completed simulated market orders, and a design document says partial fills are handled. No partial-fill fixture, restart-reconciliation test, or related broker-state trace is available.

**Finding:** `NOT VERIFIED`, yielding at least `REVIEW REQUIRED` overall if no other blockers exist. The absence of a partial fill is not itself a demonstrated defect.

**Resolution evidence:** Reproducible partial-fill/cancellation sequence demonstrating filled versus remaining quantity, no duplicate entry, consistent position and pending-order exposure, and recovery after restart.

**Escalation:** If a controlled test instead demonstrates that a partial fill causes an additional unintended full-size entry, change the finding to `BLOCKED` and cite that observed test.

## Case 5: Exposure control exists only in configuration

**Declared operator policy:** A strategy must not exceed 10% of portfolio equity in one stock, including effective exposure from pending orders. The percentage is an illustrative operator choice, **not an Alpaca limit or universal recommendation**.

**Observed evidence:** Configuration contains `max_symbol_weight: 0.10`, but the only live submission path uses a fixed notional order without consulting the policy. A test demonstrates the policy check is bypassed for the observed route.

**Finding:** `BLOCKED`. The app can violate its own stated policy, regardless of the presence of a setting named like a control.

**Resolution evidence:** Enforced policy over current positions plus relevant pending exposure; tests around the exact threshold, simultaneous orders, and failure when portfolio equity is unavailable.

## Case 6: Paper fills do not establish live execution assumptions

**Available evidence:** A backtest and paper trial show profitable trades, but the report gives no bid/ask spread, quoted-liquidity, slippage, latency, or order-type fill assumptions. The system may still have adequate operational controls elsewhere.

**Finding:** `NOT VERIFIED` for the execution-assumptions topic. Paper profitability is not a defect and is not evidence that live fills will match.

**Resolution evidence:** A documented fill model and limitations, order-type-specific stress scenarios, fee assumptions, and a human assessment of whether modeled execution is meaningful for the strategy's holding period and liquidity.

## Positive-control example: Evidence-complete within stated scope

**Available evidence (hypothetical):** One reviewed code revision is linked to the deployed artifact; all applicable review topics have scoped `VERIFIED` findings with dated tests or logs; non-applicable categories have explicit reasons; operator risk policies are documented and enforced by tests; no known defect remains open. No unreviewed order path or unknown environment remains.

**Overall:** `NO BLOCKERS FOUND` within that narrow reviewed scope. The output must still state **human deployment decision: NOT MADE BY THIS SKILL**. Do not call it `READY` or imply that the operator should enable live trading. New revisions, configurations, or incidents require renewed review.

## Quick outcome checks

| Finding set | Overall outcome |
| --- | --- |
| One `BLOCKED`, several `VERIFIED` | `BLOCKED` |
| No `BLOCKED`, one `NOT VERIFIED` | `REVIEW REQUIRED` |
| All applicable findings `VERIFIED`, justified `NOT APPLICABLE` remainder, scope known | `NO BLOCKERS FOUND` |
| All visible checks pass but deployed revision unknown | `REVIEW REQUIRED` |
| Policy threshold missing and no failure observed | `REVIEW REQUIRED` |

## Example finding entry

```text
Area: Order lifecycle
Finding: NOT VERIFIED
Evidence/inspection scope: Inspected src/execution/order_manager.py and
  test_order_manager.py at commit 123abc; tests cover filled/rejected but
  do not exercise a timeout after broker acceptance.
Next action: Add accepted-but-timed-out test, demonstrate lookup by the
  original client_order_id, and verify no duplicate submission.
Owner: Execution maintainer
```

Illustrative paths and commit hashes above must not be copied as though they came from a real review.
