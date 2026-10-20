---
name: alpaca-trading-live-readiness
description: >
  Review an automated Alpaca Trading API system for evidence of operational
  readiness before a human considers live deployment. Use after backtesting
  or paper trading, before enabling live execution, or after a material change
  to strategy, order handling, risk controls, or deployment configuration.
---

# Trading API Live-Readiness Review

Assess a trading system's **operational evidence**, not its investment merit. The question is: *What has been demonstrated, what is known to be defective, and what still needs human review before real capital is exposed?*

This is an **inspection-only** workflow. It never authorizes live deployment, places or cancels orders, changes brokerage or application settings, enables live credentials, or tests live execution. Producing local review artifacts is permitted. A favorable report is not certification, an investment recommendation, or a substitute for the operator's approval.

The skill can inspect an existing Python, JavaScript/TypeScript, CLI, MCP, or other Alpaca Trading API application. It does not require Alpaca credentials for a repository/offline review. If information is unavailable, record the limitation instead of fetching data with undisclosed privileges or filling gaps with assumptions.

## Required disclosure

Include the following in every exported review report:

> **Important disclosure:** This review is an evidence-limited operational assessment for educational and informational purposes, not investment advice, a compliance certification, a guarantee of safety, or authorization to trade live. It does not evaluate whether a strategy will make money. Backtests and paper trading do not establish future performance; live outcomes may differ because of spreads, slippage, liquidity, market impact, latency, fees, order handling, and data differences. Loss of capital is possible. The operator remains responsible for verification and deployment decisions. Review [Alpaca disclosures](https://alpaca.markets/disclosures).

When evaluating options or crypto, add asset-specific risk disclosures from Alpaca's current disclosures rather than assuming the equities disclosure alone is sufficient.

## Inputs and prerequisites

Gather, without guessing:

- Workspace or repo location and revision/commit being reviewed.
- Execution architecture, strategy or strategies, asset classes, order paths, and deployment target.
- Operator-defined policies, if any: per-order notional, maximum position and concentration, daily loss, leverage, permitted instruments, and what constitutes a safe shutdown.
- Available tests, paper activity, order logs, incident notes, and prior review artifacts, with timestamps where applicable.
- Whether the inspection is offline only. **Default to offline.** Any authenticated read-only API access requires explicit permission, and must not be used to place, change, or cancel anything.

If live trading is already enabled, report that fact and its evidence. Do not disable or alter it. Do not request API keys in chat, display secrets, store credentials in report files, or include live account identifiers where unnecessary. For CLI-backed read-only inspection, consult installed `alpaca --help`, command-specific `--help`, and `--schema` rather than assuming command flags or field names. Never use order-mutating calls to establish readiness.

## Review procedure

Follow these steps in order. Do not jump from finding one apparently good control to an overall positive assessment.

### 1. Freeze the reviewed scope

Record repository revision, files or services actually inspected, configuration names (without secrets), available logs and their date ranges, and test execution timestamps. Identify which services or deployment files **were not** accessible. Distinguish observed runtime behavior from documentation and proposed architecture. If the deployed revision cannot be linked to the reviewed code, that is unresolved evidence.

### 2. Map the path from decision to order

Trace signal source -> trade direction -> sizing -> validation -> approval or policy gate -> order request -> acknowledgement -> fills -> positions -> reconciliation -> restart/shutdown. List each path for the relevant asset classes. Find alternate paths such as direct SDK calls, webhook handlers, retries, scheduled jobs, manual overrides, and AI-agent/MCP tools. A diagram or narrative is insufficient without identifiable code or runtime evidence.

### 3. Review critical controls

For each topic below, record observable evidence and a result. Never invent a numerical limit, assume all strategies require a stop order, or equate an operator's stated policy with tested enforcement.

| Topic | Questions to investigate |
| --- | --- |
| Environment and authority | Can paper and live endpoints or credentials be confused? Can an automated process bypass human authorization or risk policy? Is execution disabled on unknown environment configuration? |
| Trade-direction consistency | For a declared long entry, is a take-profit target above entry and a downside stop below, when those labels and order mechanics apply? For shorts, is the relationship reversed? Are opening versus closing orders distinguished? |
| Sizing and exposure | Are documented order, position, gross/net exposure, concentration, leverage, and daily-loss policies enforced in all order paths? Are existing positions and pending orders included as appropriate? |
| Order lifecycle | Are accepted, rejected, canceled, replaced, partially filled, and expired orders handled without assuming a submission equals a fill? Are orders and broker positions reconciled on restart? |
| Uncertain responses | Following a timeout or lost acknowledgement, does the system resolve broker-side state and the original `client_order_id` before attempting another placement? Is retry behavior tested against duplicate exposure? |
| Market and model assumptions | Are feed, timestamps, adjustment mode, market calendar, sessions, and execution assumptions known? Are critical backtest/paper-to-live differences documented? |
| Failure response | Are data staleness, connectivity loss, process restart, failed risk checks, and emergency shutdown behaviors defined and tested? Do protective exits remain possible during a halt where appropriate? |
| Monitoring and ownership | Are fills, exposure, errors, limit breaches, and stale service conditions observable? Is a human owner and escalation path identified? |

Apply asset-class-specific rules only when relevant and supported by current Alpaca documentation or the installed tool schema. A successful paper order, a green backtest, or a passing mock test is evidence about that narrow event, **not** proof of production behavior. Reference [worked review cases](reference.md) to calibrate classifications.

### 4. Grade **each finding**, not a narrative impression

Use only these finding statuses:

- **VERIFIED:** Specific evidence demonstrates the stated control within a stated scope and revision. Identify source, date, and what the evidence actually proves. Source code alone may verify configuration or a branch of logic, but not recovery under real outages.
- **BLOCKED:** An observed defect or demonstrated missing required control creates a plausible path to unintended orders, excess exposure, unapproved live execution, or inability to recover order state. Cite the precise evidence and failure mechanism. Do not label a mere lack of evidence as a proven defect.
- **NOT VERIFIED:** The relevant control may exist, but the review lacks sufficient evidence, tests, access, freshness, or policy definition. Specify what demonstration is needed.
- **NOT APPLICABLE:** The control does not apply to the reviewed architecture or asset class, with an explicit justification. An uninspected system is **not** `NOT APPLICABLE`.

A failing test is a concrete observation; establish whether it represents an active defect, a deliberately rejected unsupported use case, or a stale test before assigning `BLOCKED`. Where policies are not defined, mark the policy-dependent check `NOT VERIFIED` and ask for a human decision; do not prescribe a supposedly safe percentage.

### 5. Determine the **overall review outcome**

Use the following deterministic precedence:

1. **BLOCKED** if at least one applicable finding is `BLOCKED`.
2. Otherwise **REVIEW REQUIRED** if at least one applicable finding is `NOT VERIFIED`, or if the scope/revision cannot be established.
3. Otherwise **NO BLOCKERS FOUND** only when all applicable review topics are `VERIFIED`, and all non-applicable topics have defensible explanations.

`NO BLOCKERS FOUND` means only that this limited review found no blockers. **It is not “READY,” does not approve live trading, and must not trigger deployment or credential changes.** A human decides whether the scope, evidence quality, strategy risk, and independent review warrant further action.

### 6. Produce the report and handoff

Use the exact structure below. Every finding must link to concrete evidence, or describe the inspection attempted and why evidence was missing. Keep findings short and specific enough for a developer to reproduce or resolve.

```text
# Alpaca Trading API Live-Readiness Review
Reviewed scope: <repo, revision, services, environments>
Assessment date: <date and timezone>
Evidence window: <dates of tests, logs, paper runs>
Overall: BLOCKED | REVIEW REQUIRED | NO BLOCKERS FOUND

| Area | Finding | Evidence / inspection scope | Next action | Owner |
| ...  | VERIFIED / BLOCKED / NOT VERIFIED / NOT APPLICABLE | path:line, test name/result, log ID/date, or evidence gap | ... | ... |

Observed blockers: <specific issue IDs or none>
Evidence still needed: <test or record needed, or none>
Out of scope: <missing components or intentional exclusions>
Changes since prior review: <revision/config delta or unknown>
Human deployment decision: NOT MADE BY THIS SKILL
Required disclosure: <text above>
```

If local file-writing is appropriate, write `live-readiness-report.md`. Do not overwrite prior reports without permission. Record the reviewed revision so a later code change does not silently inherit a favorable finding. The report must disclose that it cannot rule out defects in unreviewed code, dependencies, infrastructure, brokerage conditions, or future market behavior.

## Guardrails

- **No trade mutations:** Do not submit, replace, cancel, liquidate, or simulate a live order; do not alter policy settings or credentials. This is a review, not a live smoke test.
- **No automatic approval:** Never turn a finding into deployment authorization, even if all reviewed items are verified.
- **No manufactured evidence:** Do not create hypothetical tests and present them as tests that ran. Clearly distinguish example scenarios, recommended tests, and observed results.
- **No silent substitution:** An assertion such as "the agent checks risk" without executable evidence is `NOT VERIFIED`.
- **No fixed universal limits:** Numerical risk parameters are operator-defined. Missing policy is an evidence gap; policy violation is a defect only when the policy and execution path are established.
- **No unqualified safety claims:** `client_order_id`, a stop order, paper profitability, signal parity, or a hash chain alone cannot guarantee safe execution.
- **Protect risk-reducing actions:** Review whether halts and controls allow appropriate protective exits and broker reconciliation; do not recommend indiscriminately blocking all order actions.
- **No credential exposure:** Refer to environment variable names such as `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`, never their values.

## Related skills and references

- [Backtesting](../backtest/SKILL.md): historical research and reproducibility.
- [Paper trading](../paper-trading/SKILL.md): simulated order entry and order lifecycle.
- [Paper trading via MCP](../paper-trading-mcp/SKILL.md): MCP-specific paper execution.
- [Alpaca Trading API documentation](https://docs.alpaca.markets/us/docs/trading-api).
- [Working with orders](https://docs.alpaca.markets/us/docs/working-with-orders).
- [Paper trading](https://docs.alpaca.markets/us/docs/paper-trading).
- [Alpaca disclosures](https://alpaca.markets/disclosures).

If other proposed skills for signal parity or decision audit are merged, consume their evidence as inputs; do not duplicate their implementation.
