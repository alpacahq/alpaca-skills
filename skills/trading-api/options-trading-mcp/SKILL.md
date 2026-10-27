---
name: alpaca-trading-options-trading-mcp
description: >
  Research and structure defined-risk US options strategies on your Alpaca account
  using the Alpaca Trading API MCP Server. Agent asks you to choose paper or live
  and, if multiple Alpaca MCP server entries are configured, pick which one to
  authenticate with before any account call, asks investment outlook, shortlists
  2–3 catalog structures for user selection, then preview/place orders via MCP
  when explicitly requested. Self-contained: catalog, education, payoff,
  comparison, examples (Parts II–VI). Not investment advice.
---

# Alpaca Options Trading — MCP Server Version

Use this skill when you want your AI agent to help you **explore** defined-risk US options strategies on Alpaca using the **Alpaca Trading API MCP Server** — in **either paper or live**, your choice.

Your agent **asks whether this session is paper or live, and (if more than one Alpaca MCP server is configured) which one to use, before any account call**, then **asks your investment outlook first**, shortlists **≥2–3** catalog structures for **you to select**, and only calls order MCP tools when you **explicitly** request execution. It does **not** recommend a specific trade or open with an order ticket.

This skill is written for you, a Trading API user working with your own Alpaca account(s). Your agent calls MCP tools directly — no CLI installation or raw HTTP requests needed — and stays within the **25-strategy catalog** in **Part II**. Presentations are objective — **not investment advice**.

This is the MCP-server-specific version. A CLI version is also available as a companion skill. For a dedicated paper-only equity/crypto workflow that hard-blocks live credentials, use `alpaca-trading-paper-trading-mcp` instead.

MCP tool calls do **not** need `required_permissions: ["all"]`.

---

## 0 — How your AI agent should use this skill

1. **Ask paper or live, then pick the Alpaca MCP server, before any account tool call.** Ask: "Paper or live trading for this session?" Do not assume paper. Call `GetDynamicTools` with `{"pattern": "alpaca"}` (or similar) to discover **every** Alpaca-like namespace available — the user may have a single entry, or separate entries for paper and live. If more than one matching namespace exists, list them and ask the user which to use — never pick silently. If only one exists, you will confirm in Step 2 that it actually matches what the user asked for; if it doesn't, tell the user they need to add or reconfigure an MCP server entry for the other environment rather than proceeding on the wrong one.

2. **Verify the chosen namespace matches what the user asked for.** Paper versus live is set solely by `ALPACA_PAPER_TRADE` in the MCP server's `env` block, and no tool reports it. Read **only that one field** for the server entry backing the chosen namespace, following the single-field extraction in [`alpaca-trading-paper-trading-mcp`](../paper-trading-mcp/SKILL.md) Step 12 — never read the config wholesale, because the same block holds the API keys. Classify:
   - **PAPER** when the flag is absent, `true`, `1`, or `yes`
   - **LIVE** for any other value (including `false`)
   - Fail closed (STOP) if the config is unreadable or the entry is missing

   Then discover the account tool with `GetDynamicTools`, call it, and show only the full `account_number` plus `PAPER` or `LIVE`. If this **disagrees** with the user's stated choice in Step 1, **STOP** and surface the mismatch — do not proceed on either environment or silently fall back to the other namespace. Repeat both facts in every order preview. Stop if the account number is missing. Do not display API keys, secrets, or credential variable names.

3. **Ask subjective outlook first** if missing (underlying, direction, horizon, max loss budget). Do not ask the user to recall holdings or events when Alpaca MCP data tools are available.

4. **Discover context tools** with `GetDynamicTools`: search for positions, corporate actions, and news capabilities **on the chosen namespace**. Query positions for the underlying. For events, require a tool backed by Alpaca's [`GET /v1/corporate-actions`](https://docs.alpaca.markets/us/reference/corporateactions-1); pass the underlying symbol, today/target-expiry date window, `data_quality=all`, and paginate all results. Inspect dividends, splits, mergers, spin-offs, reorganizations, redemptions, and all other returned action types. Query News separately and label news-derived earnings/catalyst dates unconfirmed because Alpaca has no dedicated earnings-calendar endpoint.

5. **Handle connector gaps safely.** If the MCP server lacks Corporate Actions or News tools, state exactly what could not be checked. Do not fall back to CLI/HTTP in this MCP skill; ask the user only for material missing context.

6. **Shortlist ≥2–3 structures** from **Part V** using verified account/event context — objective comparison; **you select** the catalog strategy #.

7. **Teach when needed.** **Part III** (modules A–K).

8. **Run payoff calculator** (**Part IV**) after **you** select a structure — re-run when strikes or credit change.

9. **Reconfirm environment and namespace before execution.** Repeat the full `account_number` and `PAPER` or `LIVE`. Re-read `ALPACA_PAPER_TRADE` for the chosen entry. On **live**, the preview must carry a real-money warning and submission requires the user to type the literal word `LIVE` — `confirmation_mode` has no effect on this gate.

10. **Execute only on explicit request** — chain/snapshot research, order preview with MCP arguments, then confirm or auto-submit per `confirmation_mode` (paper) or typed `LIVE` (live).

11. **Monitor** positions/orders after submit, on the same namespace verified in Steps 1–2.

---

## 1 — Prerequisites

### Required

- **Alpaca Trading API MCP Server** installed in your agent host — [alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server)
- **API key and secret for each environment you want to use** in MCP server env — never pasted into chat or passed as tool arguments
- At least one MCP namespace discoverable via `GetDynamicTools`; two (one paper, one live) if you want your agent to offer a real choice each session

### MCP server configuration (Cursor, v2)

The [alpaca-mcp-server](https://github.com/alpacahq/alpaca-mcp-server) README is the source of truth for the package name, command, and environment variables. See [`alpaca-trading-paper-trading-mcp`](../paper-trading-mcp/SKILL.md) §1 for the full variable table.

Each MCP server entry is wired to **one** environment via `ALPACA_PAPER_TRADE`. To support both paper and live, configure **two** entries (names are yours to choose):

```json
{
  "mcpServers": {
    "alpaca-paper": {
      "command": "uvx",
      "args": ["alpaca-mcp-server"],
      "env": {
        "ALPACA_API_KEY": "your-paper-key",
        "ALPACA_SECRET_KEY": "your-paper-secret",
        "ALPACA_PAPER_TRADE": "true"
      }
    },
    "alpaca-live": {
      "command": "uvx",
      "args": ["alpaca-mcp-server"],
      "env": {
        "ALPACA_API_KEY": "your-live-key",
        "ALPACA_SECRET_KEY": "your-live-secret",
        "ALPACA_PAPER_TRADE": "false"
      }
    }
  }
}
```

The server derives the API host from `ALPACA_PAPER_TRADE`, so there is no base-URL variable to set or verify. With only one entry configured, your agent can only offer the environment that entry is wired to — it tells you which one and asks you to add the other entry if you want a choice.

If `namespaceStatus: "needsAuth"` → authenticate via `mcp_auth`, then retry.

If namespace is `"error"` or not found → tell you to fix MCP config. Do **not** fall back to HTTP or CLI when this is the MCP skill.

---

## 2 — Gather inputs

| Parameter | Required | Default | Notes |
|---|---|---|---|
| `account_mode` | Yes | **Ask if missing — no default** | `paper` or `live` |
| `intent` | Yes | `structure` | `research` / `structure` / `execute` |
| `strategy` | Yes (execute) | — | **You select** from shortlist; one of 25 from **Part II** |
| `underlying` | Yes (structure/execute) | — | e.g., `SPY` |
| `account_positions` | Automatic | MCP position tool | Failed lookup means unknown, not zero |
| `upcoming_events` | Automatic | MCP Corporate Actions + News tools | Search through target expiry; news dates unconfirmed |
| `units` | Yes (execute) | `1` | Whole strategy units |
| `legs[]` | Yes (execute) | — | OCC symbols, sides, intents, ratios |
| `type` | Yes | `limit` | `limit` or `market` |
| `limit_price` | If limit | — | Net debit/credit for mleg |
| `time_in_force` | Yes | `day` | `day`, `gtc` |
| `confirmation_mode` | No | `on` | `on` = yes after preview; `off` = auto-submit after preview (paper only — live always requires typed `LIVE`) |
| `mcp_namespace` | Yes | — | **User-selected** via `GetDynamicTools` (§0 Step 1) when more than one Alpaca-like namespace exists |

### Confirmation mode (`confirmation_mode`)

| Value | Paper behavior | Live behavior |
|-------|----------------|---------------|
| `on` (default) | Preview → **Submit? (yes / no)** → submit on yes | Preview with real-money warning → user types the literal word `LIVE` → submit |
| `off` | Preview → **submit immediately** (no yes/no) | **No effect.** Live ignores `confirmation_mode: off` — typing `LIVE` is always required |

Set at session start or per trade (`on` | `off`). Your agent records the active value, the chosen namespace, and the environment in every preview and `notes.md`.

**Paper, `off`:** preview remains mandatory (legs, limit, max loss, payoff summary, environment). No yes/no prompt.

**Paper, `on`:** require explicit yes before every submit.

**Live, any `confirmation_mode`:** preview carries a real-money warning. Submission requires the user to type the literal word `LIVE` — not "yes." Never auto-submitted, even with `confirmation_mode: off`.

`confirmation_mode` governs order entry only on paper. Exercise instructions always require an explicit yes (paper or live).

Wheel and multi-step workflows: each **order submit** follows this logic independently.


### Strategy confirmation checklist

Before order preview, your agent confirms:

- [ ] You stated `paper` or `live`, picked a namespace (if more than one matched), and the verified `ALPACA_PAPER_TRADE` environment matches
- [ ] Full `account_number` and `PAPER` or `LIVE` shown before account-based results and in the preview
- [ ] Holdings were queried from Alpaca; failed lookups are marked unknown
- [ ] Corporate Actions + News were searched, or unavailable MCP capabilities were disclosed
- [ ] News-derived event dates are labeled unconfirmed
- [ ] User **selected** strategy from shortlist (not agent-recommended)
- [ ] Strategy from 25-strategy catalog; max loss stated
- [ ] All MCP tool arguments match preview
- [ ] Options approval level sufficient
- [ ] Stock held for covered structures (via position tools)
- [ ] `options_buying_power` sufficient
- [ ] Relevant education modules covered (or waived)

---

## 3 — Source-of-truth references

| Source | URL | Used for |
|---|---|---|
| Alpaca Trading API docs | https://docs.alpaca.markets/us/docs/trading-api | Order/account fields |
| Options trading | https://docs.alpaca.markets/us/docs/options-trading | Levels, contracts |
| Options Level 3 / mleg | https://docs.alpaca.markets/us/docs/options-level-3-trading | Multi-leg rules |
| Alpaca MCP Server | https://github.com/alpacahq/alpaca-mcp-server | Tool schemas |
| Corporate Actions | https://docs.alpaca.markets/us/reference/corporateactions-1 | Dividends, splits, mergers, other announced actions |
| News API | https://docs.alpaca.markets/us/reference/news-3 | Earnings/catalyst signals (not authoritative calendar dates) |
| Options Disclosure Document | https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document | Risk disclosure |
| Alpaca disclosures | https://alpaca.markets/disclosures | Broker disclosures |

### Discovery rule

Your agent **must** call `GetDynamicTools` before every session. Tool names and parameters vary by MCP server version.

---

## 4 — Workflow

### Phase 0: Environment and namespace selection (every session)

```
GetDynamicTools { "pattern": "alpaca" }
```

Ask the user "paper or live?" If more than one Alpaca-like namespace is returned, list them and ask which to use. If only one exists, confirm in Phase 3 that it matches.

### Phase 1: Strategy confirmation

Map intent to one of 25 strategies. Restate outlook and max loss. Wait for your confirmation.

### Phase 2: Education gate

Relevant **Part III** modules for new users or short premium.

### Phase 3: Tool discovery and account verification

```
GetDynamicTools { "namespace": "<chosen-id>", "toolName": "place_option_order" }
```

Classify environment from `ALPACA_PAPER_TRADE` for the chosen server entry (§0 Step 2), extracting only that field — the same `env` block holds the API keys:

```bash
jq -r '.mcpServers | keys[]' ~/.cursor/mcp.json
jq -r '.mcpServers | has("<server-name>")' ~/.cursor/mcp.json
jq -r '.mcpServers["<server-name>"].env.ALPACA_PAPER_TRADE // "unset"' ~/.cursor/mcp.json
```

Substitute the host's own config path when it is not Cursor. `unset` (absent) classifies as paper only when the entry was confirmed to exist; a missing entry or unparseable config is inconclusive and fails closed. The server lowercases the value and accepts exactly `true`, `1`, or `yes` as paper — any other value selects live.

Then call the account tool (`get_account_info` as of v2). Verify `status` = `ACTIVE`, `trading_blocked` = false, `options_trading_level` (the effective level) ≥ strategy need, and adequate `options_buying_power`. The account response never proves environment on its own — live and paper accounts return the same shape.

**STOP** if the classified environment does not match what the user asked for in Phase 0.

### Phase 4: Research

1. Chain / contracts — filter underlying, expiration, strike, call/put
2. Snapshots — bid/ask, Greeks, IV. On **0DTE**, Greek fields may be null when \(T - t \to 0\); use quotes and intrinsic value — see **Part III** Module D
3. Stock positions — for covered call, collar, covered strangle, wheel
4. Rule of 16 — when discussing earnings vol (Module E)

Do not use web search for quotes when MCP option tools are available.

### Phase 5: Order preview

Build exact `place_option_order` arguments from the discovered tool schema, not from the REST body — the tool reshapes it. Show preview table (namespace, `PAPER`/`LIVE`, legs, max loss) and `confirmation_mode`. On **paper**: if `on`, ask **Submit? (yes / no)**; if `off`, invoke after preview. On **live**: always show the real-money warning and require the user to type the literal word `LIVE` — `confirmation_mode` does not change this.

### Phase 6: Submit and monitor

Call `place_option_order` after your yes (paper) or typed `LIVE` (live). Monitor with order/position tools (`get_order_by_id`, `get_all_positions` as of v2) on the same namespace verified in Phase 3.

---

## 5 — Output contract

```
runs/<YYYYMMDD-HHMMSS>-options-trading-mcp/
  notes.md
  orders.json          # MCP request/response captures
  order_log.csv
  contracts.json       # chain/snapshot selections
  review.md
```

MCP responses are not auto-saved — your agent writes `orders.json` explicitly.

---

## 6 — Execution rules

1. **Environment and namespace first** — ask paper or live, discover Alpaca-like namespaces with `GetDynamicTools`, let the user pick when more than one exists
2. **Discover tools first** — never hard-code tool names
3. **No default environment** — never assume paper; verify every session that the chosen namespace's `ALPACA_PAPER_TRADE` matches stated intent
4. **No HTTP/CLI fallback** when MCP is healthy
5. **25 strategies only**
6. **No financial advice**
7. **Re-discover on schema errors**

---

## 7 — Validation and tests

Before every submit, re-run the strategy confirmation checklist in §2 and the **Part IV** payoff for the quoted strikes. After submit, confirm the order status and report rejections, partial fills, and remaining quantity.

---

## 8 — Disclosures, safety, and data handling

> Options involve significant risk and are not suitable for all investors. Read the [Options Disclosure Document](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document). Paper trading is simulated and may not reflect live fills, fees, or liquidity. **Live trading risks real money** — losses can exceed the premium paid on short-option positions. This material is not investment advice. Review [Alpaca disclosures](https://alpaca.markets/disclosures).

Never pass API keys as tool arguments. Session artifacts stay on your local filesystem. Repeat the live-specific warning on every live preview.

---

## 9 — Anti-patterns

- **NEVER** assume paper (or live) — ask which environment the session uses before any account call
- **NEVER** auto-select an Alpaca MCP namespace when more than one is discovered — list them and let the user choose
- **NEVER** proceed on a namespace whose `ALPACA_PAPER_TRADE` disagrees with the user's stated environment
- **NEVER** use account data or preview an order without showing the full `account_number` and whether the server is `PAPER` or `LIVE`
- **NEVER** treat an account response as proof of environment, or read the MCP config wholesale to check `ALPACA_PAPER_TRADE`
- **NEVER** recommend a specific trade or invoke order MCP tools before the user selects a structure and sets execute intent
- **NEVER** shortlist fewer than 2 catalog structures when matching an outlook (unless only one valid after exclusions)
- **NEVER** ask the user for holdings before attempting an Alpaca position tool
- **NEVER** present Alpaca News as an authoritative earnings calendar
- **NEVER** silently skip event checks when the MCP server lacks the required tool
- **NEVER** hard-code MCP tool names without `GetDynamicTools`
- **NEVER** pass API keys as tool arguments
- **NEVER** accept "yes" (or anything other than the literal word `LIVE`) as sufficient to submit a live order
- **NEVER** let `confirmation_mode: off` bypass the typed `LIVE` confirmation on a live namespace
- **NEVER** skip the order preview
- **NEVER** skip submit confirmation when `confirmation_mode` is `on` (paper)
- **NEVER** automate excluded strategies
- **NEVER** use `required_permissions: ["all"]` for MCP calls
- **NEVER** fall back to CLI/HTTP when MCP is the chosen execution path
- **NEVER** map index options to the equity 25-strategy catalog
- **NEVER** exercise an option without explicit confirmation, regardless of `confirmation_mode`

---

## 10 — Related content in this file

| Part | Section | Contents |
|---|---|---|
| **I** | §0–§9 above | MCP workflow, namespace/environment selection, tool discovery |
| **II** | Strategy Catalog | All 25 strategies |
| **III** | Education Modules | Modules A–K |
| **IV** | Payoff Calculator | Breakeven engine (#1–25) |
| **V** | Strategy Comparison | Outlook map and side-by-side workflow |
| **VI** | Examples | MCP workflow examples |

### Companion skills

| Skill | Description |
|---|---|
| `alpaca-trading-options-trading-cli` | CLI execution version |
| `alpaca-trading-paper-trading-mcp` | Dedicated paper-only equity/crypto MCP workflow — hard-blocks live |
| `alpaca-trading-backtest` | Historical signals |

---

# Part II — Strategy Catalog (25)

Alpaca execution mapping for each strategy. Definitions align with standard retail options education and the curated set in this skill.

**Asset scope:** US listed **equity and ETF** options (American-style, 100-share multiplier). Index options (SPX, etc.) are a separate Alpaca product — not mapped to this catalog (see education Module K).

**Alpaca constraints**

- Multi-leg orders: `order_class: mleg`, **2–4 legs**, no equity leg in the same order
- `ratio_qty` values must be in simplest form (GCD = 1)
- Contract multiplier: **100 shares** per contract
- See **Part III** Module D for **0DTE Greeks** (Black–Scholes when \(T - t \to 0\))
- See **Part IV** for max profit, max loss, breakevens, and expiry P&L tables (every strategy)
- See **Part V** to filter and compare strategies by outlook, risk, and expiration

**Approval level key**

| Tag | Meaning |
|-----|---------|
| L1 | Covered call, cash-secured put |
| L2 | Long call, long put |
| L3 | Spreads and 2–4 leg strategies via `mleg` |

Always verify the account's current `options_trading_level` — the effective level, which can be lower than `options_approved_level`.

---

## Tier 1 — Foundations

### 1. Long Call

| Field | Detail |
|-------|--------|
| **Outlook** | Bullish |
| **Structure** | Buy 1 call |
| **Max loss** | Premium paid |
| **Max gain** | Theoretically unlimited |
| **Alpaca** | Single-leg; L2; `buy` + `buy_to_open` |
| **Where it breaks** | Sideways market (theta); IV crush after entry; wrong timing |

### 2. Long Put

| Field | Detail |
|-------|--------|
| **Outlook** | Bearish or hedge |
| **Structure** | Buy 1 put |
| **Max loss** | Premium paid |
| **Max gain** | Substantial (strike − premium, floor at zero) |
| **Alpaca** | Single-leg; L2; `buy` + `buy_to_open` |
| **Where it breaks** | Slow grind higher; IV contraction |

### 3. Covered Call (Buy/Write)

| Field | Detail |
|-------|--------|
| **Outlook** | Neutral to slightly bullish |
| **Structure** | Long 100+ shares + sell 1 OTM call per 100 shares |
| **Max loss** | Stock decline (partially offset by premium) |
| **Max gain** | Call strike − stock basis + premium (capped above strike) |
| **Alpaca** | Stock position must exist; short call single-leg L1; `sell` + `sell_to_open` |
| **Notes** | Watch **dividends** and early assignment on deep ITM calls |
| **Where it breaks** | Strong rally through short strike; selling calls too close to ex-div |

### 4. Cash-Secured Put (CSP)

| Field | Detail |
|-------|--------|
| **Outlook** | Bullish to neutral (willing to own stock) |
| **Structure** | Sell 1 put; cash reserved for assignment at strike |
| **Max loss** | Strike − premium (if stock → 0) |
| **Max gain** | Premium received |
| **Alpaca** | Single-leg; L1; `sell` + `sell_to_open`; verify cash/margin |
| **Where it breaks** | Gap down through strike; overconcentration |

### 5. Protective Put (Married Put)

| Field | Detail |
|-------|--------|
| **Outlook** | Bullish but seeking downside floor |
| **Structure** | Long 100+ shares + buy 1 put |
| **Max loss** | Stock basis − put strike + put premium (floored) |
| **Max gain** | Unlimited above premium cost |
| **Alpaca** | Stock + long put (two orders or existing stock + buy put); put leg L2 |
| **Where it breaks** | Premium drag in flat markets; put strike too far OTM |

### 6. Collar (Protective Collar)

| Field | Detail |
|-------|--------|
| **Outlook** | Neutral to slightly bullish; protect stock |
| **Structure** | Long stock + long put (floor) + short OTM call (ceiling) |
| **Max loss** | Limited by put strike |
| **Max gain** | Limited by call strike |
| **Alpaca** | Requires stock; **two option legs** in one `mleg` if stock already held; L3 |
| **Notes** | Call premium offsets put cost; zero-cost collar when balanced |
| **Where it breaks** | Rally capped at short call; put too far OTM for real protection |

### 7. Put Spread Collar

| Field | Detail |
|-------|--------|
| **Outlook** | Protection at lower net cost |
| **Structure** | Long stock + long put + short call + **short lower-strike put** |
| **Max loss** | Floored between the put strikes; below the short put, losses resume (stock toward zero, offset by the put-spread width) |
| **Max gain** | Capped at short call |
| **Alpaca** | 3 option legs in `mleg` + stock; L3 |
| **Where it breaks** | Sharp drop below short put; four-part complexity |

### 8. Covered Strangle (Covered Combination)

| Field | Detail |
|-------|--------|
| **Outlook** | Neutral; income on stock |
| **Structure** | Long stock + short OTM call + short OTM put |
| **Max loss** | Stock decline + put obligation (not undefined if stock owned) |
| **Max gain** | Call strike − stock basis + both premiums (capped at the call strike) |
| **Alpaca** | Stock + 2-leg `mleg` (short call + short put); L3 |
| **Where it breaks** | Large move either direction; assignment on put adds shares |

---

## Tier 1 — Vertical Spreads

All verticals: same expiration, different strikes, 2-leg `mleg`.

### 9. Bull Call Spread (Debit)

| Legs | Buy lower-strike call; sell higher-strike call |
| **Outlook** | Moderately bullish |
| **Max loss** | Net debit |
| **Max gain** | Strike width − debit |
| **Alpaca** | L3; [Alpaca long call spread example](https://docs.alpaca.markets/us/docs/options-level-3-trading) |

### 10. Bear Call Spread (Credit)

| Legs | Sell lower-strike call; buy higher-strike call |
| **Outlook** | Neutral to bearish |
| **Max loss** | Width − credit |
| **Max gain** | Net credit |
| **Alpaca** | L3 |

### 11. Bull Put Spread (Credit)

| Legs | Sell higher-strike put; buy lower-strike put |
| **Outlook** | Bullish to neutral |
| **Max loss** | Width − credit |
| **Max gain** | Net credit |
| **Alpaca** | L3; common defined-risk income spread |

### 12. Bear Put Spread (Debit)

| Legs | Buy higher-strike put; sell lower-strike put |
| **Outlook** | Bearish |
| **Max loss** | Net debit |
| **Max gain** | Width − debit |
| **Alpaca** | L3; [Alpaca long put spread example](https://docs.alpaca.markets/us/docs/options-level-3-trading) |

**Vertical spread failure modes:** price stalls inside short strike; IV crush hurts debit spreads; credit spreads challenged by fast moves through short strike.

---

## Tier 2 — Time & Volatility

### 13. Long Calendar Spread

| Field | Detail |
|-------|--------|
| **Structure** | Sell near-term option; buy same-strike longer-term option |
| **Outlook** | Neutral near term; benefits from near-term decay |
| **Alpaca** | 2-leg `mleg`, **different expirations** on same strike |
| **Where it breaks** | Large early move; back-month IV compression |

### 14. Diagonal Spread

| Field | Detail |
|-------|--------|
| **Structure** | Long longer-dated option + short nearer-dated OTM option |
| **Outlook** | Mild directional bias + income on short leg |
| **Alpaca** | 2-leg `mleg`, different strikes and expirations |
| **Where it breaks** | Price runs to short strike quickly |

### 15. Long Straddle

| Field | Detail |
|-------|--------|
| **Structure** | Buy ATM call + buy ATM put (same strike/expiry) |
| **Outlook** | Large move either direction |
| **Alpaca** | 2-leg `mleg` debit |
| **Where it breaks** | Move smaller than implied; post-event IV crush |

### 16. Long Strangle

| Field | Detail |
|-------|--------|
| **Structure** | Buy OTM call + buy OTM put |
| **Outlook** | Cheaper vol play than straddle |
| **Alpaca** | 2-leg `mleg` debit |
| **Where it breaks** | Range-bound; strikes too far OTM |

---

## Tier 2 — Range & Pin

### 17. Iron Condor

| Field | Detail |
|-------|--------|
| **Structure** | Bull put spread + bear call spread (4 legs) |
| **Outlook** | Neutral / range-bound |
| **Max gain** | Net credit |
| **Max loss** | Wider wing width − credit |
| **Alpaca** | 4-leg `mleg`; L3; [Alpaca iron condor example](https://docs.alpaca.markets/us/docs/options-level-3-trading) |
| **Notes** | Defined outcomes at entry; assignment risk on short legs |
| **Where it breaks** | Sustained trend; vol spike through short strikes |

### 18. Iron Butterfly

| Field | Detail |
|-------|--------|
| **Structure** | Short ATM straddle + long OTM wings (4 legs) |
| **Outlook** | Strong pinning at center strike |
| **Max gain** | Net credit |
| **Max loss** | Wing width − credit |
| **Alpaca** | 4-leg `mleg`; L3 |
| **Where it breaks** | Early move away from ATM strike |

### 19. Long Call Butterfly

| Field | Detail |
|-------|--------|
| **Structure** | Buy 1 lower call; sell 2 middle calls; buy 1 upper call |
| **Outlook** | Neutral, target middle strike |
| **Alpaca** | 3-leg `mleg`; ratio **1 : 2 : 1** |
| **Where it breaks** | Price away from body before expiry |

### 20. Long Put Butterfly

| Field | Detail |
|-------|--------|
| **Structure** | Buy 1 higher put; sell 2 middle puts; buy 1 lower put |
| **Outlook** | Neutral, target middle strike |
| **Alpaca** | 3-leg `mleg`; ratio 1 : 2 : 1 |
| **Where it breaks** | Same as long call butterfly |

---

## Tier 2 — Income Cycles

### 21. Wheel Strategy

| Field | Detail |
|-------|--------|
| **Structure** | CSP → assignment → covered call → repeat |
| **Outlook** | Income + accumulation in sideways/gentle trends |
| **Alpaca** | Sequence of L1 single-leg orders |
| **Where it breaks** | Sustained downtrend; passive management |

### 22. Poor Man's Covered Call (PMCC)

| Field | Detail |
|-------|--------|
| **Structure** | Long LEAP call + short near-term OTM call |
| **Outlook** | Bullish with less capital than stock |
| **Alpaca** | Long LEAP (L2) + short call; often two orders |
| **Where it breaks** | Choppy underlying; short calls cap recovery |

---

## Tier 3 — Repair & Defined Convexity

### 23. Call Backspread

| Field | Detail |
|-------|--------|
| **Structure** | Sell 1 lower-strike call; buy 2+ higher-strike calls (ratio 1:2) |
| **Outlook** | Bullish with convex upside |
| **Alpaca** | 2-leg `mleg` ratio 1:2; L3 |
| **Where it breaks** | Stalls below long strikes |

### 24. Put Backspread

| Field | Detail |
|-------|--------|
| **Structure** | Sell 1 higher-strike put; buy 2 lower-strike puts |
| **Outlook** | Bearish with convex downside |
| **Alpaca** | 2-leg `mleg` ratio 1:2; L3 |
| **Where it breaks** | Sharp rebound after entry |

### 25. Stock Repair

| Field | Detail |
|-------|--------|
| **Structure** | Long stock (underwater) + buy 1 ATM call + sell 2 OTM calls |
| **Outlook** | Recover basis without adding cash to stock |
| **Alpaca** | Stock already held + 2-leg `mleg`, `ratio_qty` 1 and 2; L3 |
| **Where it breaks** | Rally through upper strikes; short call assignment |

---

## Excluded strategies (reference)

These common retail and automation strategies are **out of scope** for this skill:

Short straddle, short strangle, ratio spread, box spread, conversion/reversal, synthetic long/short/synthetic covered call, jade lizard, broken-wing butterfly, Christmas tree, hedged iron fly, vol arb (IV vs HV), calendar strangles/diagonal condors, earnings IV crush engine, pre-market IV expansion, post-earnings drift automation, macro/OPEX gamma workflows.

---

# Part III — Education Modules

Foundational concepts for your agent. **Not investment advice.**

Primary Alpaca references:

- [Options Trading](https://docs.alpaca.markets/us/docs/options-trading)
- [Options Level 3 / mleg](https://docs.alpaca.markets/us/docs/options-level-3-trading)
- [How To Trade Options with Alpaca](https://alpaca.markets/learn/how-to-trade-options-with-alpaca) (includes 0DTE and index options)
- [Market Data FAQ — Greeks](https://docs.alpaca.markets/us/docs/market-data-faq)
- [Options Disclosure Document (ODD)](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document)

Use these modules to **gate** execution for newer users when appropriate.

---

## Module A — Contract mechanics (foundation)

**When:** Before any first trade in a session.

**Cover:**

1. **What an option is** — contract for right (long) or obligation (short), not ownership (except when assigned on short puts/calls).
2. **Calls vs puts** — call: right to buy; put: right to sell.
3. **Strike & expiration** — fixed terms; **US equity options are American-style** (exercise anytime before expiry).
4. **Premium** — paid by buyer to seller; non-refundable to buyer.
5. **Multiplier** — 1 contract = 100 shares for US **equity/ETF** options (Alpaca default).
6. **Catalog scope** — this skill's 25 strategies assume **equity/ETF underlyings** with share delivery on assignment (see Module K for index options).

**Your agent checkpoint:** You can explain what happens if you **buy** vs **sell** a call at expiration.

---

## Module B — Exercise & assignment

**When:** Before selling options or holding through expiration week.

**Cover:**

1. **Long options** — holder may exercise (American equity options) or let expire worthless.
2. **Short options** — assignment risk when ITM; may receive/deliver shares.
3. **Automatic exercise** — Alpaca/OCC process for ITM at expiry (typically ≥ $0.01 ITM) unless DNE.
4. **Insufficient buying power at expiry** — if ITM and account cannot exercise, Alpaca may **liquidate within ~1 hour of expiry**.
5. **Early assignment** — more likely on deep ITM short calls **before ex-dividend**.
6. **Manual exercise API** — `POST /v2/positions/{contract}/exercise`; exercises **all** contracts of that symbol.
7. **Exercise timing** — requests **between market close and midnight are rejected**.
8. **DNE** — contact Alpaca support on live; not an API field.
9. **Monitoring** — poll account activities for `OPEXC`, `OPASN`, `OPEXP`; assignments are not on websocket.

**Your agent checkpoint:** You know a short **call** on a dividend-paying stock may assign early; a short **put** assigns into long stock; you warn about expiry-day liquidation if BP is tight.

---

## Module C — Dividends & short calls

**When:** Before covered calls or CSPs on dividend payers.

**Cover:**

1. Dividends reduce call extrinsic value; deep ITM calls may trade below intrinsic.
2. Early assignment on short calls can occur to capture dividend.
3. Avoid selling calls blindly through ex-div without checking dates.

**Your agent should:** If ex-div is within 7 days and the short call is deep ITM, warn you about early assignment risk.

---

## Module D — Greeks as risk context (not prediction)

**When:** Before spreads, condors, or any multi-leg trade.

**Cover (plain language):**

| Greek | Retail meaning |
|-------|----------------|
| **Delta** | Directional exposure (share-equivalent) |
| **Gamma** | How fast delta changes; higher near ATM short-dated |
| **Theta** | Time decay; helps short premium, hurts long premium |
| **Vega** | Sensitivity to implied volatility |

Greeks are **context tools** for understanding sensitivity — not price predictions. Market-maker hedging can amplify intraday moves on short-dated options.

**Your agent checkpoint:** You know long options lose value from time decay if price stalls.

### When Greek fields are null

Alpaca uses **Black–Scholes** ([Market Data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq)). Greeks are often null when:

- **0DTE** — \(T - t \to 0\) (division by zero in the model)
- **Zero bid or ask** on the contract quote
- **No recent underlying SIP trade**
- **Deep OTM / near expiry** — IV solver fails to converge

A null Greek does not imply zero delta. Use **quotes**, **intrinsic value**, and strategy **max loss**. Approximate delta proxies: deep ITM ≈ ±1; ATM ≈ ±0.5; deep OTM ≈ 0.
---

## Module E — Rule of 16 & implied move

**When:** Before earnings-related long straddle/strangle discussions.

**Cover:**

1. **Rule of 16:** Annual IV ÷ 16 ≈ expected daily move (%) as rough heuristic.
2. Compare implied move from straddle price to historical earnings moves.
3. Tail risk — large gaps can exceed implied move.

**Your agent should:** Show an implied move estimate; note that past earnings gaps may exceed it.

---

## Module F — Seller discipline (income strategies)

**When:** Before bull put spread, bear call spread, iron condor, covered call, CSP, wheel.

**Cover:**

1. **Defined risk vs undefined** — prefer spreads over naked short premium for retail.
2. **Position sizing** — max loss at entry should fit risk budget.
3. **Management** — plan for breach of short strike (roll, close, accept assignment).
4. **mleg rolls** — some 4-leg rolls (calendar/strike rolls) may be **rejected** if Alpaca sees uncovered shorts in the same mleg; test on paper or close/open separately.
5. **Why short straddle/strangle are excluded from this skill** — unlimited risk; use iron condor or vertical credit spreads instead.
6. **Credit vertical strike economics** — max loss at entry = **spread width − net credit** (per share, ×100 per contract). Moving to a strike pair that collects **less credit** (e.g., a tighter bear call spread such as 1780/1830 vs a wider pair) **increases max loss dollar-for-dollar** if width is unchanged, and often increases it when width narrows but credit falls more. **Re-run Part IV** for each strike pair — never reuse max loss from a different width or quote.

**Your agent checkpoint:** You can state max loss for the **actual** strikes quoted and explain how a credit change affects width − credit.

---

## Module G — Protection & income on stock (collar family)

**When:** Before protective put (#5), collar (#6), put spread collar (#7), or covered strangle (#8).

**Cover:**

1. **Protective put (married put)** — long stock + long put; downside floor at put strike; cost = put premium. Core hedge when you want to keep shares but cap loss.
2. **Collar (protective collar)** — long stock + long put (floor) + short OTM call (ceiling). Call premium offsets put cost; zero-cost collar when premiums balance. Caps upside above short call.
3. **Put spread collar** — collar plus **short lower-strike put**; lower net cost than plain collar; protection floor stops at the short put strike (not zero).
4. **Covered strangle (covered combination)** — long stock + short OTM call + short OTM put. Neutral income on a stock you already own; not undefined risk when stock backs both shorts. Watch large moves and put assignment.

**Your agent checkpoint:** You can state max loss for your chosen structure and whether you hold enough shares (100 per short call contract).

---

## Module H — Condors & butterflies

**When:** Before iron condor (#17), iron butterfly (#18), long call butterfly (#19), or long put butterfly (#20).

**Cover:**

1. **Iron condor** — put credit spread + call credit spread; range-bound view; max loss = wing width − credit.
2. **Iron butterfly** — short ATM straddle + long OTM wings; pin at center strike; max loss = wing width − credit.
3. **Long call butterfly** — buy 1 lower call, sell 2 middle calls, buy 1 upper call (ratio **1 : 2 : 1**); debit; profits if price pins near middle strike at expiry.
4. **Long put butterfly** — buy 1 higher put, sell 2 middle puts, buy 1 lower put (1 : 2 : 1); same pin logic on the downside side.
5. **Defined max loss at entry** — compute width − credit (credit structures) or net debit (long butterflies).
6. **Assignment risk** on short legs near expiry; model P&L at a few underlying prices before submitting.

**Your agent checkpoint:** You know long butterflies are **debit** structures targeting a strike, unlike iron condors (credit + range).

---

## Module J — Repair & convexity

**When:** Before call backspread (#23), put backspread (#24), or stock repair (#25).

**Cover:**

1. **Call backspread** — sell 1 lower-strike call, buy 2+ higher-strike calls (ratio 1:2 in this catalog). Defined-risk convex bullish play; opposite of a ratio spread (which is excluded).
2. **Put backspread** — sell 1 higher-strike put, buy 2 lower-strike puts. Defined-risk convex bearish play.
3. **Stock repair** — long underwater stock + buy 1 ATM call + sell 2 OTM calls. Attempts to recover basis without adding cash to the stock; max outcome capped by short calls. That is **two option legs** (`ratio_qty` 1 and 2) on stock already held — not a three-leg order.

**Your agent should:** Map backspreads and stock repair to a 2-leg `mleg` with simplified ratios (GCD = 1); show max loss before submit. For stock repair, verify stock is already held and do not add the shares as an option leg.

---

## Module I — Required disclosures

Always include before order placement:

- [Characteristics and Risks of Standardized Options (ODD)](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document)
- [Alpaca disclosures](https://alpaca.markets/disclosures)
- Options not suitable for all investors; possible loss of entire premium on long options

---

## Module K — Alpaca platform notes

**When:** Before first execution in a session or when platform questions arise.

**Cover:**

1. **Choose the environment first** — your agent asks paper or live before any account call; it does not default to paper. It discovers Alpaca-like namespaces with `GetDynamicTools`, lets you pick when more than one exists, classifies `PAPER`/`LIVE` from that entry's `ALPACA_PAPER_TRADE` (single-field extraction), and shows the full `account_number` with the classification. Repeat both in every order preview. Stop on a mismatch between stated and verified environment.
2. **Options enablement** — options enabled by default on paper accounts; live accounts need dashboard approval.
3. **Buying power** — check `options_buying_power` (and `buying_power`) before debits and CSPs.
4. **Contracts API defaults** — omitting `expiration_date_lte` returns only through **next weekend**; set explicit date range.
5. **GTC orders** — supported; warn about cross-session fills when you choose `gtc`.
6. **Confirmation mode** — on **paper**, `on` (default) requires yes after preview and `off` auto-submits after preview. On **live**, submission always requires the user to type the literal word `LIVE` in the preview — `confirmation_mode` has no effect on live.
7. **Structure vs execute** — shortlist **≥2–3** catalog structures from outlook; **you select** before any order preview (compliance — not investment advice).
8. **Automatic holdings context** — query Alpaca positions before shortlisting. A failed query means “unknown,” not “no shares.”
9. **Automatic event context** — query Corporate Actions through target expiry for dividends, splits, mergers, and related events; search Alpaca News for earnings/catalyst mentions.
10. **Earnings limitation** — Alpaca has no dedicated earnings-calendar endpoint. Label news-derived event dates **unconfirmed** and ask the user only when timing remains material and unresolved.
11. **Index options (SPX, etc.)** — available in **paper** separately; cash-settled, European-style; **not** in this skill's 25-strategy catalog.
12. **Unsupported** — fractional options, extended hours, stock+option in one `mleg`.

**Your agent checkpoint:** You know this skill is scoped to **equity/ETF** catalog strategies unless you explicitly expand outside it with Alpaca docs.

---

## Teaching vs executing

| Mode | Your agent behavior |
|------|---------------------|
| **Research / learn** | Teach modules A–K; no orders |
| **Structure** | Ask outlook → shortlist **≥2–3** strategies from catalog; **you select**; optional Part IV payoff — **no order preview** |
| **Execute** | Full workflow after **your** structure selection + environment/namespace verification in §0 Steps 1–2; paper uses `confirmation_mode`, live always requires typed `LIVE` |

If you skip education modules on your first session, your agent offers a one-paragraph summary of max loss and assignment risk before preview.

---

# Part IV — Payoff & Breakeven Engine

Deterministic **at-expiration** calculator for every strategy in the catalog (Part II). Your agent runs this **before** order preview whenever you structure or compare a trade.

**Not investment advice.** Results assume European-style expiry P&L (intrinsic value at expiration, no early assignment unless noted). Multiply **per-share** results by **100 × units** for dollar P&L per contract set.

---

## 0 — How your agent uses this file

1. Collect inputs from you or from chain quotes (strikes, net debit/credit per share, stock basis if needed).
2. Look up the strategy section below (#1–25).
3. Compute **max profit**, **max loss**, and **breakeven(s)** using the formulas.
4. Build an **expiry payoff table** (minimum 5 underlying prices — see template in §1).
5. Show results in the order preview alongside legs and approval level.

If two strategies are under consideration, run the calculator for each and present side-by-side using **Part V**.

---

## 1 — Notation & payoff table template

| Symbol | Meaning |
|--------|---------|
| \(S\) | Underlying price **at expiration** |
| \(S_0\) | Underlying price **at entry** (for context only) |
| \(B\) | Stock basis per share (average cost) |
| \(K, K_1, K_2, \ldots\) | Strike prices (\(K_1 < K_2\) unless noted) |
| \(D\) | Net **debit** per share (money paid, positive number) |
| \(C\) | Net **credit** per share (money received, positive number) |
| \(W\) | Strike width per share: \(K_{\text{high}} - K_{\text{low}}\) for vertical wings |
| **Units** | Number of strategy units (each unit = one spread set or 1 contract per leg per ratio) |
| **Multiplier** | 100 shares per US equity option contract |

**Payoff table template** (your agent fills one row per price):

```
Strategy:     #N — {name}
Underlying:   {SYMBOL}    Spot @ entry: ${S0}    Expiry: {date}
Net entry:    ${debit or credit}/share × 100 × {units} = ${total}

| S @ expiry | P&L / share | P&L / unit ($) | Zone        |
|------------|-------------|----------------|-------------|
| ...        | ...         | ...            | max loss    |
| ...        | ...         | ...            | breakeven   |
| ...        | ...         | ...            | max profit  |
```

Pick \(S\) values: below max-loss zone, at each breakeven, at short strikes, at long strikes, at max-profit zone, and one tail beyond.

---

## 2 — Single-leg options

### #1 — Long call

**Inputs:** \(K\) (call strike), \(D\) (premium paid per share)

| Metric | Formula (per share) | Per unit ($) |
|--------|---------------------|--------------|
| **Max loss** | \(D\) | \(-D \times 100 \times \text{units}\) |
| **Max profit** | Unlimited (\(\max(S-K,0) - D\)) | — |
| **Breakeven** | \(K + D\) | — |

**Expiry P&L / share:** \(\max(S - K, 0) - D\)

---

### #2 — Long put

**Inputs:** \(K\) (put strike), \(D\)

| Metric | Formula (per share) | Per unit ($) |
|--------|---------------------|--------------|
| **Max loss** | \(D\) | \(-D \times 100 \times \text{units}\) |
| **Max profit** | \(K - D\) (at \(S=0\)) | \((K-D) \times 100 \times \text{units}\) |
| **Breakeven** | \(K - D\) | — |

**Expiry P&L / share:** \(\max(K - S, 0) - D\)

---

## 3 — Stock + option structures

Assume **1 unit = 100 shares** + option legs scaled 1:1 unless noted.

### #3 — Covered call

**Inputs:** \(B\) (stock basis), \(K\) (short call strike), \(C_c\) (call premium received per share)

| Metric | Formula (per share) | Notes |
|--------|---------------------|-------|
| **Max profit @ expiry** | \(K - B + C_c\) | When \(S \ge K\) |
| **Max loss @ expiry** | \(B - C_c\) | When \(S = 0\) (stock loss partially offset by premium) |
| **Breakeven @ expiry** | \(B - C_c\) | Stock + premium combined |

**Expiry P&L / share (100 shares):** \(\min(S, K) - B + C_c\)

---

### #4 — Cash-secured put (CSP)

**Inputs:** \(K\) (short put strike), \(C_p\) (premium received per share)

| Metric | Formula (per share) |
|--------|---------------------|
| **Max profit** | \(C_p\) (expires OTM) |
| **Max loss** | \(K - C_p\) (stock to zero if assigned) |
| **Breakeven** (if assigned) | \(K - C_p\) |

**Expiry P&L / share:** \(C_p - \max(K - S, 0)\)

---

### #5 — Protective put (married put)

**Inputs:** \(B\), \(K_p\) (long put strike), \(D_p\) (put premium paid)

| Metric | Formula (per share) |
|--------|---------------------|
| **Max loss @ expiry** | \(B - K_p + D_p\) |
| **Max profit** | Unlimited (\(S - B - D_p\) for large \(S\)) |
| **Breakeven @ expiry** | \(B + D_p\) |

**Expiry P&L / share:** \(S - B + \max(K_p - S, 0) - D_p\)

---

### #6 — Collar

**Inputs:** \(B\), \(K_p\) (long put), \(D_p\), \(K_c\) (short call), \(C_c\); net option cost \(N = D_p - C_c\) (positive = net debit)

| Metric | Formula (per share) |
|--------|---------------------|
| **Max loss @ expiry** | \(B - K_p + N\) |
| **Max gain @ expiry** | \(K_c - B - N\) |
| **Breakeven @ expiry** | \(B + N\) |

**Expiry P&L / share:** \(\min(S, K_c) - B + \max(K_p - S, 0) - N\)

---

### #7 — Put spread collar

**Inputs:** \(B\), long put \(K_{pL}\) premium \(D_{pL}\), short call \(K_c\) premium \(C_c\), short put \(K_{pS}\) premium \(C_{pS}\) where \(K_{pS} < K_{pL}\)

Net option flow per share: \(N = D_{pL} - C_c - C_{pS}\) (adjust signs if net credit)

| Metric | Formula (per share) |
|--------|---------------------|
| **Max loss @ expiry** | \(B + N - (K_{pL} - K_{pS})\) at \(S = 0\). Loss is floored at \(B - K_{pL} + N\) only between \(K_{pS}\) and \(K_{pL}\); below \(K_{pS}\) it grows again |
| **Max gain @ expiry** | \(K_c - B - N\) |
| **Breakeven @ expiry** | Solve per region below. \(B + N\) is a root **only** when \(K_{pL} \le B + N \le K_c\). If no region contains a root, report **no breakeven** |

**Expiry P&L / share** (\(K_{pS} < K_{pL} < K_c\); keep a root only if it is inside its region **and** \(\ge 0\) — stock price cannot go negative):

| Region | P&L / share | Root |
|--------|-------------|------|
| \(S < K_{pS}\) | \(S - B + (K_{pL} - K_{pS}) - N\) | \(B + N - (K_{pL} - K_{pS})\), keep only if \(0 \le \text{root} < K_{pS}\) |
| \(K_{pS} \le S < K_{pL}\) | flat \(K_{pL} - B - N\) | the whole segment, only if this equals 0 |
| \(K_{pL} \le S \le K_c\) | \(S - B - N\) | \(B + N\), keep if inside the segment |
| \(S > K_c\) | flat \(K_c - B - N\) | the whole region, only if this equals 0 |

If the first-region root is negative, there is **no breakeven in that region** — check \(S = 0\) directly: if P&L at \(S=0\) is already positive, the position profits at every reachable price and has no breakeven at all.

Example 1 (breakeven exists): basis \(80\), long put \(95\), short put \(90\), short call \(110\), \(N = 0\). \(B + N = 80\) is below \(K_{pL}\), so it is not a breakeven (P&L there is \(+5\)). The root in \(S < K_{pS}\) is \(75\), which is \(\ge 0\) — keep it.

Example 2 (no breakeven): basis \(3\), long put \(95\), short put \(90\), short call \(110\), \(N = 0\). The first-region root is \(3 + 0 - (95-90) = -2\), which is negative — reject it. P&L at \(S=0\) is \(+2\), so this position profits at every possible price; report **no breakeven**.

**Your agent must** build a 5+ row payoff table — piecewise between \(K_{pS}\), \(K_{pL}\), \(K_c\).

---

### #8 — Covered strangle

**Inputs:** \(B\), short call \(K_c\) / \(C_c\), short put \(K_p\) / \(C_p\); total credit \(C_{\text{tot}} = C_c + C_p\)

| Metric | Formula (per share) |
|--------|---------------------|
| **Max profit @ expiry** | \(K_c - B + C_{\text{tot}}\) when \(S \ge K_c\) |
| **Max loss @ expiry** | \(B + K_p - C_{\text{tot}}\) at \(S = 0\) — the stock goes to zero and the short put is assigned, so below \(K_p\) losses accrue at twice the stock's rate |
| **Breakeven** | One: \(B - C_{\text{tot}}\) when that is \(\ge K_p\); otherwise \((B + K_p - C_{\text{tot}})/2\). No upper breakeven — P&L is flat above \(K_c\) |

**Expiry P&L / share:** \(\min(S, K_c) - B + C_{\text{tot}} - \max(K_p - S, 0)\)

---

## 4 — Vertical spreads (same expiry)

Let \(W = |K_2 - K_1|\) for the two strikes.

### #9 — Bull call spread (debit)

Buy \(K_1\) call, sell \(K_2\) call (\(K_1 < K_2\)), net debit \(D\)

| Max loss | \(D\) |
| Max profit | \(W - D\) |
| Breakeven | \(K_1 + D\) |

**P&L / share:** \(\max(S-K_1,0) - \max(S-K_2,0) - D\)

---

### #10 — Bear call spread (credit)

Sell \(K_1\) call, buy \(K_2\) call, net credit \(C\)

| Max profit | \(C\) |
| Max loss | \(W - C\) |
| Breakeven | \(K_1 + C\) |

**P&L / share:** \(C - \max(S-K_1,0) + \max(S-K_2,0)\)

---

### #11 — Bull put spread (credit)

Sell \(K_2\) put, buy \(K_1\) put (\(K_1 < K_2\)), net credit \(C\)

| Max profit | \(C\) |
| Max loss | \(W - C\) |
| Breakeven | \(K_2 - C\) |

**P&L / share:** \(C - \max(K_2-S,0) + \max(K_1-S,0)\)

---

### #12 — Bear put spread (debit)

Buy \(K_2\) put, sell \(K_1\) put, net debit \(D\)

| Max loss | \(D\) |
| Max profit | \(W - D\) |
| Breakeven | \(K_2 - D\) |

**P&L / share:** \(\max(K_2-S,0) - \max(K_1-S,0) - D\)

---

## 5 — Time & volatility

### #13 — Long calendar spread

**Inputs:** Same strike \(K\); near leg credit \(C_n\), far leg debit \(D_f\); net debit \(D = D_f - C_n\)

| Metric | Guidance |
|--------|----------|
| **Max loss (typical)** | \(\approx D\) (large move in near term) |
| **Max profit** | Depends on IV and remaining far leg — **not fully captured at single expiry** |
| **Breakeven** | No single closed form — use payoff table near \(K\) at near-term expiry |

**Your agent:** Label as **approximate**; show P&L at \(S \in \{K-W, K, K+W\}\) for the near expiry event.

---

### #14 — Diagonal spread

**Inputs:** Long far leg (\(K_l\), \(D_l\)), short near leg (\(K_s\), \(C_s\)); net \(N = D_l - C_s\) (positive = net debit)

Same as calendar: **multi-expiry** — run a payoff table at **near expiry** and say whether the remaining long leg is marked at intrinsic or at a quote.

**Near-expiry loss bound** with the long marked at intrinsic. Calls: \(N\) when \(K_s \ge K_l\); \(N + (K_l - K_s)\) when the short strike is below the long strike. Puts: \(N\) when \(K_s \le K_l\); \(N + (K_s - K_l)\) when the short strike is above the long strike. Do **not** quote \(\approx N\) unless the short strike is at or beyond the long strike. A long 110 call at $5 and a short 100 call at $3 has \(N = 2\) but about **$12**/share of intrinsic loss at $110.

---

### #15 — Long straddle

**Inputs:** Strike \(K\), total debit \(D = D_{\text{call}} + D_{\text{put}}\)

| Max loss | \(D\) (at \(S = K\)) |
| Max profit | Unlimited upside; downside capped at \(K - D\) (price cannot fall below 0) |
| **Breakeven up** | \(K + D\) |
| **Breakeven down** | \(K - D\) |

**P&L / share:** \(\max(S-K,0) + \max(K-S,0) - D = |S-K| - D\)

---

### #16 — Long strangle

**Inputs:** Put strike \(K_p\), call strike \(K_c\) (\(K_p < K_c\)), total debit \(D\)

| Max loss | \(D\) (when \(K_p \le S \le K_c\)) |
| **Breakeven down** | \(K_p - D\) |
| **Breakeven up** | \(K_c + D\) |

**P&L / share:** \(\max(S-K_c,0) + \max(K_p-S,0) - D\)

---

## 6 — Range & pin

### #17 — Iron condor

**Inputs:** Put wing \(K_{p1} < K_{p2}\), call wing \(K_{c1} < K_{c2}\); short strikes \(K_{p2}\), \(K_{c1}\); net credit \(C\); wing width \(W_p = K_{p2}-K_{p1}\), \(W_c = K_{c2}-K_{c1}\) (often \(W_p = W_c = W\))

| Max profit | \(C\) |
| Max loss | \(\max(W_p, W_c) - C\) (usually \(W - C\) if equal) |
| **Breakeven lower** | \(K_{p2} - C\) |
| **Breakeven upper** | \(K_{c1} + C\) |

**P&L / share:** \(C - \max(K_{p2}-S,0) + \max(K_{p1}-S,0) - \max(S-K_{c1},0) + \max(S-K_{c2},0)\)

---

### #18 — Iron butterfly

**Inputs:** Body strike \(K\); wings \(K-w\) and \(K+w\); net credit \(C\)

| Max profit | \(C\) (at \(S = K\)) |
| Max loss | \(w - C\) |
| **Breakeven lower** | \(K - C\) |
| **Breakeven upper** | \(K + C\) |

**P&L / share:** \(C - \max(K-S,0) + \max(K-w-S,0) - \max(S-K,0) + \max(S-(K+w),0)\) — simplify with table.

---

### #19 — Long call butterfly (1 : 2 : 1)

**Inputs:** \(K_1 < K_2 < K_3\), wing \(W = K_2 - K_1 = K_3 - K_2\), net debit \(D\)

| Max loss | \(D\) |
| Max profit @ \(S=K_2\) | \(W - D\) |
| **Breakeven lower** | \(K_1 + D\) |
| **Breakeven upper** | \(K_3 - D\) |

**P&L / share:** \(\max(S-K_1,0) - 2\max(S-K_2,0) + \max(S-K_3,0) - D\)

---

### #20 — Long put butterfly (1 : 2 : 1)

**Inputs:** \(K_3 > K_2 > K_1\), wing \(W = K_3 - K_2 = K_2 - K_1\), debit \(D\)

| Max loss | \(D\) |
| Max profit @ \(S=K_2\) | \(W - D\) |
| **Breakeven lower** | \(K_1 + D\) |
| **Breakeven upper** | \(K_3 - D\) |

**P&L / share:** \(\max(K_3-S,0) - 2\max(K_2-S,0) + \max(K_1-S,0) - D\)

---

## 7 — Income cycles

### #21 — Wheel

Composite of **#4 CSP** then **#3 covered call** on assigned shares.

**Your agent:** Run calculator for **current leg only** (CSP or covered call). After assignment, re-run #3 with updated \(B\).

---

### #22 — Poor man's covered call (PMCC)

**Inputs:** Long LEAP call strike \(K_l\), debit \(D_l\); short near call \(K_s\), credit \(C_s\); net \(N = D_l - C_s\)

| Metric | Guidance |
|--------|----------|
| **Max loss** | \(\approx N\) (LEAP can go to zero) |
| **Max profit near term** | Capped when \(S \ge K_s\) at short expiry |
| **Breakeven** | \(K_l + N\) at LEAP expiry (approximate) |

Run payoff table at **short call expiry** with LEAP marked at intrinsic \(\max(S-K_l,0)\).

---

## 8 — Repair & convexity

### #23 — Call backspread (1 : 2)

**Inputs:** Short 1 call \(K_1\), long 2 calls \(K_2\) (\(K_1 < K_2\)); net debit \(D\) or credit \(-C\)

Let net entry = \(D\) if debit, or treat credit as negative \(D\).

| Max loss (typical zone) | At \(S \approx K_2\): often worst case \(\approx D + (K_2-K_1)\) — **verify with table** |
| Max profit | Unlimited for large \(S\) |
| **Breakeven upper** (approx.) | \(2K_2 - K_1 + D\) (adjust for net credit) |

**P&L / share:** \(-\max(S-K_1,0) + 2\max(S-K_2,0) - D\)

---

### #24 — Put backspread (1 : 2)

**Inputs:** Short 1 put \(K_2\), long 2 puts \(K_1\) (\(K_1 < K_2\)); net \(D\)

| Max loss (typical zone) | Near \(K_1\) — verify with table |
| Max profit | Large for \(S \to 0\) |
| **Breakeven lower** (approx.) | \(2K_1 - K_2 - D\) |

**P&L / share:** \(-\max(K_2-S,0) + 2\max(K_1-S,0) - D\)

---

### #25 — Stock repair

**Inputs:** Stock basis \(B\); buy 1 ATM call (\(K_a \approx S_0\), \(D_c\)); sell 2 OTM calls (\(K_h\), credit \(2C_s\)); net option \(N = D_c - 2C_s\)

| Metric | Guidance |
|--------|----------|
| **Max loss @ expiry** | Still substantial if \(S \to 0\) (stock + long call decay) |
| **Max gain @ expiry** | Capped near \(K_h\) when \(S \ge K_h\) |
| **Breakeven** | Build table — typically between \(S_0\) and \(K_h\) |

**P&L / share @ expiry:** \(S - B + \max(S-K_a,0) - D_c - 2\max(S-K_h,0) + 2C_s\)

---

## 9 — Quick lookup index

| # | Strategy | Max loss key | Breakeven key |
|---|----------|--------------|---------------|
| 1 | Long call | \(D\) | \(K+D\) |
| 2 | Long put | \(D\) | \(K-D\) |
| 3 | Covered call | \(B-C_c\) | \(B-C_c\) |
| 4 | CSP | \(K-C_p\) | \(K-C_p\) |
| 5 | Protective put | \(B-K_p+D_p\) | \(B+D_p\) |
| 6 | Collar | \(B-K_p+N\) | \(B+N\) |
| 7 | Put spread collar | Table | Table |
| 8 | Covered strangle | \(B+K_p-C\) | One; see #8 |
| 9 | Bull call | \(D\) | \(K_1+D\) |
| 10 | Bear call | \(W-C\) | \(K_1+C\) |
| 11 | Bull put | \(W-C\) | \(K_2-C\) |
| 12 | Bear put | \(D\) | \(K_2-D\) |
| 13 | Calendar | \(\approx D\) | Table |
| 14 | Diagonal | \(N\), or \(N\) + strike gap if the short strike is inside the long | Table |
| 15 | Long straddle | \(D\) | \(K \pm D\) |
| 16 | Long strangle | \(D\) | \(K_p-D\), \(K_c+D\) |
| 17 | Iron condor | \(W-C\) | \(K_{p2}-C\), \(K_{c1}+C\) |
| 18 | Iron butterfly | \(W-C\) | \(K \pm C\) |
| 19 | Call butterfly | \(D\) | \(K_1+D\), \(K_3-D\) |
| 20 | Put butterfly | \(D\) | \(K_1+D\), \(K_3-D\) |
| 21 | Wheel | Leg #4 / #3 | Leg #4 / #3 |
| 22 | PMCC | \(\approx N\) | Table |
| 23 | Call backspread | Table | Upper approx |
| 24 | Put backspread | Table | Lower approx |
| 25 | Stock repair | Table | Table |

---

# Part V — Strategy Comparison Guide

Use this file when you have a **market outlook** but have not chosen a strategy yet, or when you want to **compare two or more** catalog strategies side-by-side.

Pair with **Part IV** for numeric max profit, max loss, and breakevens after **you** pick a structure and strikes.

**Compliance:** Your agent lists catalog structures objectively. It does **not** recommend a specific trade or build an order until you select a strategy and request execution.

---

## 0 — How your agent compares strategies

1. **Ask your investment outlook** if missing: underlying, direction, time horizon (DTE target), and max $ loss per unit.
2. **Query account context:** retrieve Alpaca positions for the underlying. Do not ask whether stock is held unless account access fails.
3. **Query event context:** retrieve Corporate Actions through target expiry and search Alpaca News for earnings/catalyst signals. Mark news-derived dates unconfirmed; Alpaca News is not an earnings calendar.
4. **Filter** using §2 (outlook map) or §3 (master table), excluding stock-backed structures when verified available shares are insufficient.
5. **Shortlist at least 2–3** strategies that fit — never a single “recommended” trade.
6. **Present comparison table** (§4 template): outlook fit, max-loss character, capital/stock, approval level, verified holdings, and event considerations. Optional **Part IV** numbers when you supply strikes for each finalist.
7. **You choose** which catalog strategy # to explore or execute — agent does not pick for you.
8. **Execute path only after selection** — order preview and submit follow §4 Phases 5–6.

Do not recommend suitability. Present tradeoffs objectively. End with: **you select** the structure to proceed.

---

## 1 — Comparison dimensions

| Dimension | What to compare |
|-----------|-----------------|
| **Outlook** | Bullish, bearish, neutral, vol expansion, income, protection |
| **Verified holdings** | Alpaca shares/options held; shares available for covered structures |
| **Upcoming events** | Confirmed corporate actions; unconfirmed news-derived earnings/catalysts |
| **Risk** | Max loss per unit ($), defined vs stock tail risk |
| **Expiration** | Typical DTE; theta-friendly (short premium) vs long premium |
| **Max profit** | Cap vs unlimited; credit vs debit entry |
| **Breakevens** | Count and distance from spot |
| **Capital** | Stock required? Cash-secured? Debit amount |
| **Approval** | L1 / L2 / L3 |
| **Legs** | Single vs mleg count |

---

## 2 — Outlook → strategy map

| Your outlook | Start here (# = strategy catalog) | Also consider |
|--------------|-----------------------------------|---------------|
| **Strong bullish** | #1 Long call, #9 Bull call spread | #23 Call backspread, #22 PMCC |
| **Moderate bullish** | #9 Bull call spread, #11 Bull put spread | #3 Covered call, #4 CSP, #21 Wheel |
| **Bearish** | #2 Long put, #12 Bear put spread | #10 Bear call spread, #24 Put backspread |
| **Moderate bearish / neutral-bear** | #10 Bear call spread | #17 Iron condor (call side wider) |
| **Neutral / range** | #17 Iron condor, #18 Iron butterfly | #19/#20 Long butterflies, #8 Covered strangle |
| **Large move either way** | #15 Long straddle, #16 Long strangle | — |
| **Protect stock** | #5 Protective put, #6 Collar | #7 Put spread collar |
| **Income on stock held** | #3 Covered call, #8 Covered strangle | #6 Collar (protection + cap) |
| **Income without stock** | #4 CSP, #11 Bull put spread | #21 Wheel, #17 Iron condor |
| **Recover underwater stock** | #25 Stock repair | #5 Protective put (if adding protection only) |
| **Pin at strike** | #19/#20 Long butterfly, #18 Iron butterfly | #17 Iron condor (range, not pin) |

**Excluded:** naked short straddle/strangle — offer #17, #11, or #10 instead.

---

## 3 — Master comparison table (all 25)

Typical DTE is guidance only — you choose expirations. Max profit/loss summarizes **structure**; run **Part IV** for dollars.

| # | Strategy | Outlook | Typical DTE | Entry | Max profit (structure) | Max loss (structure) | Breakevens | Stock? | Level | Legs |
|---|----------|---------|-------------|-------|------------------------|----------------------|------------|--------|-------|------|
| 1 | Long call | Bullish | 30–90 | Debit | Unlimited | Premium | 1 | No | L2 | 1 |
| 2 | Long put | Bearish / hedge | 30–90 | Debit | Substantial | Premium | 1 | No | L2 | 1 |
| 3 | Covered call | Neutral–bull | 30–45 | Credit | Capped @ call | Stock ↓ | 1 | Yes | L1 | 1 opt |
| 4 | CSP | Bull–neutral | 30–45 | Credit | Premium | Strike − prem | 1 | No* | L1 | 1 |
| 5 | Protective put | Bull + floor | 30–180 | Debit | Unlimited | Floored | 1 | Yes | L2 | 1 opt |
| 6 | Collar | Protect + cap | 30–90 | Mixed | Capped @ call | Floored @ put | 1 | Yes | L3 | 2 opt |
| 7 | Put spread collar | Cheaper protect | 30–90 | Mixed | Capped | Floored, then stock ↓ below short put | Table | Yes | L3 | 3 opt |
| 8 | Covered strangle | Neutral income | 30–45 | Credit | Capped @ call | Stock + put ↓ | 1 | Yes | L3 | 2 opt |
| 9 | Bull call spread | Mod bull | 30–60 | Debit | Width − debit | Debit | 1 | No | L3 | 2 |
| 10 | Bear call spread | Bear–neutral | 30–45 | Credit | Credit | Width − credit | 1 | No | L3 | 2 |
| 11 | Bull put spread | Bull–neutral | 30–45 | Credit | Credit | Width − credit | 1 | No | L3 | 2 |
| 12 | Bear put spread | Bearish | 30–60 | Debit | Width − debit | Debit | 1 | No | L3 | 2 |
| 13 | Long calendar | Neutral near | Near + far | Debit | Variable | ≈ debit | Table | No | L3 | 2 |
| 14 | Diagonal | Mild bias | Near + far | Mixed | Variable | \(N\), plus strike gap if inverted | Table | No | L3 | 2 |
| 15 | Long straddle | Vol ↑ | 7–45 | Debit | Unlimited ↑; ↓ capped at \(K - D\) | Total prem | 2 | No | L3 | 2 |
| 16 | Long strangle | Vol ↑ cheap | 7–45 | Debit | Unlimited ↑; ↓ capped at \(K_p - D\) | Total prem | 2 | No | L3 | 2 |
| 17 | Iron condor | Range | 30–45 | Credit | Credit | Wing − credit | 2 | No | L3 | 4 |
| 18 | Iron butterfly | Pin | 30–45 | Credit | Credit | Wing − credit | 2 | No | L3 | 4 |
| 19 | Long call fly | Pin (calls) | 30–45 | Debit | Wing − debit | Debit | 2 | No | L3 | 3 |
| 20 | Long put fly | Pin (puts) | 30–45 | Debit | Wing − debit | Debit | 2 | No | L3 | 3 |
| 21 | Wheel | Income cycle | 30–45 | Credit | Premium steps | CSP max loss | Per leg | Optional | L1 | seq |
| 22 | PMCC | Bull LEAP | LEAP + short | Mixed | Capped | LEAP cost | Table | No | L2+ | 2 |
| 23 | Call backspread | Convex bull | 45–90 | Debit/cred | Unlimited ↑ | Zone loss | 1–2 | No | L3 | 2 |
| 24 | Put backspread | Convex bear | 45–90 | Debit/cred | Large ↓ | Zone loss | 1–2 | No | L3 | 2 |
| 25 | Stock repair | Repair basis | 60–180 | Mixed | Capped ↑ | Tail ↓ | Table | Yes | L3 | 2 opt |

\*CSP requires cash to secure assignment.

---

## 4 — Side-by-side template (your agent fills)

When you ask “compare X vs Y” or “what fits moderate bullish 45 DTE”:

```
Comparison — {SYMBOL} @ ${spot} — target expiry ~{date}

| | #9 Bull call | #11 Bull put | #3 Covered call* |
|---|-------------|-------------|------------------|
| Outlook fit | Moderate bull | Bull–neutral | Neutral–slight bull |
| Net entry | $0.95 debit | $1.20 credit | $1.10 credit |
| Max profit / unit | $405 | $120 | $310 (capped) |
| Max loss / unit | $95 | $380 | Stock tail |
| Breakeven(s) | $211.95 | $218.80 | $208.90 |
| Theta | Negative | Positive | Positive |
| Needs stock | No | No | Yes (100 sh) |
| Approval | L3 | L3 | L1 |

*Include only if you hold shares.

Payoff @ expiry (per unit $):
| S | #9 | #11 | #3 |
|---|----|----|-----|
| ... | ... | ... | ... |

Recommendation: none — you select based on your outlook and risk budget.
```

Always include **max profit, max loss, breakevens** from **Part IV** for the actual strikes quoted.

---

## 5 — Common comparison prompts

| You say | Agent action |
|---------|--------------|
| “What should I trade on AAPL?” | **Ask outlook first** — do not propose an order; then shortlist ≥2 structures |
| “Moderately bullish, limited risk” | Compare #9 vs #11 vs #4 (≥2 required) |
| “Neutral, earn premium” | Compare #17 vs #11+#10 vs #8 (if stock) |
| “Earnings play, big move” | Compare #15 vs #16; Module E in **Part III** |
| “Protect my shares” | Compare #5 vs #6 vs #7 |
| “Income on stock I own” | Compare #3 vs #8 vs #6 |
| “Range vs pin” | Compare #17 iron condor vs #19 long butterfly |

---

## 6 — Risk tier (for filtering)

| Tier | Strategies | Max loss character |
|------|------------|-------------------|
| **Premium paid (capped)** | #1, #2, #9, #12, #15, #16, #19, #20 | Known debit |
| **Credit spread (defined)** | #10, #11, #17, #18 | Width − credit |
| **Stock + options** | #3, #5, #6, #7, #8, #25 | Stock + option combo |
| **Convex / table required** | #13, #14, #22, #23, #24, #25 | Run full payoff table |

---

## 7 — Expiration sensitivity (qualitative)

| Profile | Favors | Examples |
|---------|--------|----------|
| **Short DTE (7–21)** | Theta on short premium; vol plays | #17, #11, #15 (event) |
| **Medium (30–45)** | Balance theta / cost | Most spreads, condors |
| **Long (60–180+)** | Protection, LEAP structures | #5, #22, #25 |

When comparing strategies with **different DTE profiles**, state the assumption explicitly in the comparison table.

---

# Part VI — Examples

Assume tools discovered via `GetDynamicTools`. Names below are **illustrative**.

**Pattern:** Ask paper or live → pick namespace (if multiple) → ask outlook → shortlist **≥2–3** structures → **user selects** → MCP order tools only when asked.

---

## Example -1 — Choosing paper vs live with multiple MCP server entries

**User:** Help me trade options on AAPL.

**Agent:**

1. Ask: "Paper or live trading for this session?"
2. Discover namespaces:

```
GetDynamicTools { "pattern": "alpaca" }
```

3. If more than one namespace is returned (e.g., `alpaca-paper` and `alpaca-live`), list them and ask which to use. If only one exists, note which environment it is wired to.
4. Read **only** `env.ALPACA_PAPER_TRADE` for the chosen server entry (single-field extraction — see §0 Step 2). Classify `PAPER` or `LIVE`.
5. Call the account tool; show full `account_number` and classification. **STOP** if it disagrees with Step 1.

---

## Example 0 — Outlook shortlist (no order tool)

**User:** Ideas for options on AAPL?

**Agent:** After Example -1 environment/namespace selection: ask only for direction, DTE, and max loss. Discover and call Alpaca position, Corporate Actions, and News tools before shortlisting. If event tools are unavailable, disclose the gap; never silently assume no events. Label news-derived dates unconfirmed. Shortlist ≥2 catalog structures from **Part V**. Do **not** call `place_option_order` until user selects a structure and requests execution.

---

## Example 1 — Discover and verify the chosen environment

```
GetDynamicTools pattern: "alpaca"
# user picks namespace if multiple
Read env.ALPACA_PAPER_TRADE only, for the matching server entry (see §0 Step 2)
CallDynamicTool get_account_info
```

Agent classifies `PAPER` or `LIVE` from the config flag, confirms it matches the user's stated intent, then verifies `options_trading_level >= 3` for iron condor.

---

## Example 2 — Iron condor (after user selects #17)

**User:** Neutral SPY — what structures fit? *(Agent shortlists ≥2.)* **User:** Paper iron condor (#17).

1. Confirm user selected strategy #17 from **Part II** and re-verify the namespace is paper.
2. `get_option_chain` for SPY with target expiration.
3. `get_option_snapshot` on four candidate OCC symbols.
4. Preview:

```
Strategy: Iron Condor SPY
Namespace: alpaca-paper
Environment: PAPER
Units: 1
Net limit: $1.80 credit
Max loss: $320
Tool: place_option_order
Legs: [4 legs with intents]
```

5. If paper and `confirmation_mode: on`, user confirms yes; if paper and `off`, skip prompt. If live, require typed `LIVE`.
6. `CallDynamicTool place_option_order` with confirmed payload.
7. `get_order_by_id` with returned id.

---

## Example 3 — Long call (level 2)

```
get_option_chain AAPL → select call
get_option_snapshot → set limit near ask
place_option_order buy_to_open 1 contract
```

---

## Example 4 — Reject excluded strategy

**User:** Run earnings IV crush automation.

**Your agent:** Excluded workflow (earnings IV crush automation, not in the 25-strategy catalog). Offer manual long straddle/strangle research with Module E (Rule of 16) instead — no automated engine.

---

## Example 5 — Collar on held stock

```
get_open_position AAPL → qty >= 100
get_option_chain → select put floor + call ceiling
place_option_order 2-leg mleg: buy put, sell call
```

Warn on dividends (education Module C).

---

## Example 6 — MCP namespace missing

If `GetDynamicTools` returns no alpaca namespace:

> Alpaca MCP server not configured. Install per https://github.com/alpacahq/alpaca-mcp-server with a paper and/or live entry (`ALPACA_PAPER_TRADE` `true` or `false`). Alternatively use `alpaca-trading-options-trading-cli`.

Do not fall back to curl in this skill.

---

## Example 7 — `confirmation_mode: off` on paper

**User:** Execute the previewed iron condor on paper without asking yes/no.

**Agent:** Confirm paper via `ALPACA_PAPER_TRADE` → preview with `confirmation_mode: off` → `place_option_order` → `get_order_by_id`.

---

## Example 8 — Live order requires typing `LIVE`, even with `confirmation_mode: off`

**User:** Live trade the previewed iron condor. Don't ask me to confirm — `confirmation_mode: off`.

**Agent:**

1. Confirm the chosen namespace's `ALPACA_PAPER_TRADE` classifies as live.
2. Show preview with real-money warning, namespace, `LIVE`, and max loss.
3. User replies "yes" → **reject**. Require the literal word `LIVE`.
4. User types `LIVE` → `place_option_order`. `confirmation_mode: off` does not skip this gate.
