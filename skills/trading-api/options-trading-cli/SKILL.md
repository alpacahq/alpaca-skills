---
name: alpaca-trading-options-trading-cli
description: >
  Research and structure defined-risk US options strategies on your Alpaca account
  using the Alpaca CLI. Agent asks you to choose paper or live and pick the CLI
  profile to authenticate with before any Alpaca call, asks investment outlook,
  shortlists 2–3 catalog structures for user selection, then preview/submit via
  alpaca CLI when explicitly requested. Self-contained: strategy catalog,
  education, payoff, comparison, examples, CLI reference (Parts II–VII). Not
  investment advice.
---

# Alpaca Options Trading — CLI Version

Use this skill when you want your AI agent to help you **explore** defined-risk US options strategies on Alpaca using the **`alpaca` CLI** — in **either paper or live**, your choice.

Your agent **asks whether this session is paper or live, and which CLI profile to use, before any Alpaca call**, then **asks your investment outlook first**, shortlists **≥2–3** catalog structures for **you to select**, and only runs CLI order commands when you **explicitly** request execution. It does **not** recommend a specific trade or open with an order ticket.

This skill is written for you, a Trading API user working with your own Alpaca account, CLI profile(s), and local workspace. Your agent executes all operations through the `alpaca` command-line tool, stays within the **25-strategy catalog** in **Part II**, and presents tradeoffs objectively — **not investment advice**.

This is the CLI-specific version. An MCP-server version is also available as a companion skill. For a dedicated paper-only equity/crypto workflow that hard-blocks live credentials, use `alpaca-trading-paper-trading-cli` instead.

**All shell commands require `required_permissions: ["all"]`.** Run outside the sandbox so the CLI can access local authentication. The CLI prints JSON by default; filter it with the built-in `--jq` flag.

---

## 0 - How your AI agent should use this skill

1. **Ask paper or live, then pick the CLI profile, before any other Alpaca call.** Ask: "Paper or live trading for this session?" Do not assume paper. Run `alpaca profile list --json` and show the available profiles. If more than one profile exists, ask the user which one to use — never pick silently, even if a profile name looks obviously right. If only one profile exists, confirm with the user that it's the one they want. Set the chosen profile as `ALPACA_PROFILE` for the session — **never** pass `-p`/`--profile` per command, since some commands honor it and others (like `alpaca doctor`) ignore it, which can make the check and the order resolve to different endpoints.

2. **Verify the chosen profile matches what the user asked for.** Run `alpaca doctor` and `alpaca account get --jq '.account_number'`. Show only the full `account_number` and **PAPER** or **LIVE**, classified from the `Trading:` line `alpaca doctor` reports (`https://paper-api.alpaca.markets` = paper; `https://api.alpaca.markets` = live) — not from the profile name alone, since a profile named "paper" can still resolve to live if `ALPACA_LIVE_TRADE` is set. If the resolved environment **disagrees** with what the user said in Step 1, **STOP** and surface the mismatch — do not proceed on either environment or let the user override by re-stating intent without fixing the profile. Repeat both facts in every order preview. Stop if `account_number` is missing. Do not display API keys, secrets, or credential variable names.

3. **Ask subjective outlook first** if missing (underlying, direction, horizon, max loss budget). Do not ask the user to recall holdings or events when Alpaca CLI access is available.

4. **Enrich from Alpaca CLI before shortlisting.** Run `alpaca position list` and match the underlying. Then use `alpaca data corporate-actions`—the CLI wrapper for Alpaca's [`GET /v1/corporate-actions`](https://docs.alpaca.markets/us/reference/corporateactions-1)—with symbol, start, end, `data_quality=all`, and pagination through target expiry. Inspect dividends, splits, mergers, spin-offs, reorganizations, redemptions, and all other returned types. Run `alpaca data news` separately for earnings/catalyst evidence. Use `--help`/`--schema` to discover installed flags. Label news-derived dates unconfirmed; Alpaca has no dedicated earnings calendar.

5. **Shortlist ≥2–3 structures** from **Part V** using the verified holding/event context — objective comparison; **you select** the catalog strategy #. No “recommended” trade.

6. **Teach when needed.** **Part III** (modules A–K).

7. **Run payoff calculator** (**Part IV**) after **you** select a structure — re-run when strikes or credit change (Module F).

8. **Execute only on explicit request** — gather legs, show CLI preview + exact command, then confirm or auto-submit per `confirmation_mode` (paper) or typed `LIVE` (live).

9. **Reconfirm environment and profile before execution.** Repeat the full `account_number` and `PAPER` or `LIVE`. Re-run `alpaca doctor`. On **live**, the preview must carry a real-money warning and submission requires the user to type the literal word `LIVE` — `confirmation_mode` has no effect on this gate.

10. **Discover contracts** — `alpaca data option chain` (**Part VII**).

11. **Show order preview** with account number, `PAPER` or `LIVE`, the active CLI profile name, payoff table, the full CLI command(s), and the `--dry-run` request body — **never** before the user selects a structure and asks to execute.

12. **Confirm before submit** — on **paper**, `confirmation_mode: on` (default) prompts yes/no after preview and `off` auto-submits after preview. On **live**, submission always requires the user to type `LIVE`, regardless of `confirmation_mode`.

13. **Submit** — `alpaca order submit` (single-leg, or `--order-class mleg --legs` for multi-leg).

14. **Monitor** — `alpaca order get --order-id`, `alpaca position list`. If credentials or profile change mid-session, re-run Steps 1–2.

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

> The CLI is in **Alpha Preview**. Commands, flags, and output formats may change between releases, so your agent discovers flags with `--help` rather than trusting any list in this file.

### Profile(s) configured for the environment(s) you'll use

```bash
alpaca profile login --api-key
alpaca profile list --json
alpaca doctor
```

Set up a profile for each environment you expect to use (e.g., one paper profile, one live profile). Your agent lists and picks between them at session start (§0 Step 1) — it does not assume there's only one.

### Runtime

| Requirement | Detail |
|---|---|
| CLI profile | At least one configured; agent lists and picks one each session (§0 Step 1) |
| Options enabled | Paper: enabled by default; live: needs dashboard approval; confirm `options_trading_level` (the effective level) ≥ strategy need |
| `--jq` | Built-in filter for the CLI's JSON output; external `jq` is not required |
| Strategy catalog | **Part II** (below) |
| Education | **Part III** |
| Payoff / breakeven | **Part IV** (below) |
| Compare strategies | **Part V** (below) |

---

## 2 - Gather inputs

| Parameter | Description | Default | Required |
|---|---|---|---|
| `account_mode` | `paper` or `live` | **Ask if missing — no default** | Yes |
| `intent` | Research, structure, or execute | **`structure`** | Yes |
| `strategy` | One of 25 from **Part II** | **You select** from shortlist | Yes (execute) |
| `underlying` | e.g., `SPY`, `AAPL` | — | Yes (structure/execute) |
| `account_positions` | Shares/options held | Query `alpaca position list` | Automatic |
| `upcoming_events` | Corporate actions + news-derived catalysts | Query `alpaca data` commands through target expiry | Automatic |
| `units` | Strategy units (whole contracts) | `1` | Yes (execute) |
| `order_type` | `limit` or `market` | `limit` | Yes |
| `limit_price` | Net debit/credit for `mleg` | From quotes | Conditional |
| `position_intent` | Per leg | Inferred | Yes (options) |
| `time_in_force` | `day`, `gtc` | `day` | Yes |
| `confirmation_mode` | `on` = yes after preview; `off` = auto-submit after preview (paper only — live always requires typed `LIVE`) | `on` | No |
| `profile` | CLI profile name | **User-selected** from `alpaca profile list --json` (§0 Step 1) | Yes |

### Confirmation mode (`confirmation_mode`)

| Value | Paper behavior | Live behavior |
|-------|----------------|---------------|
| `on` (default) | Preview → **Submit? (yes / no)** → submit on yes | Preview with real-money warning → user types the literal word `LIVE` → submit |
| `off` | Preview → **submit immediately** (no yes/no) | **No effect.** Live ignores `confirmation_mode: off` — typing `LIVE` is always required |

Set at session start or per trade (`on` | `off`). Your agent records the active value, the chosen profile, and the environment in every preview and `notes.md`.

**Paper, `off`:** preview remains mandatory (legs, limit, max loss, payoff summary, environment, profile). No yes/no prompt.

**Paper, `on`:** require explicit yes before every submit.

**Live, any `confirmation_mode`:** preview carries a real-money warning. Submission requires the user to type the literal word `LIVE` — not "yes." This is never auto-submitted, even with `confirmation_mode: off`.

`confirmation_mode` governs order entry only on paper. Exercise instructions always require an explicit yes (paper or live).

Wheel and multi-step workflows: each **order submit** follows this logic independently.


### Strategy confirmation checklist

Before building orders, your agent confirms:

- [ ] You stated `paper` or `live`, picked a profile from `alpaca profile list --json`, and the verified `alpaca doctor` environment matches
- [ ] Full `account_number` and `PAPER` or `LIVE` shown before account-based results and in the preview
- [ ] Holdings were queried from Alpaca; failed lookups are marked unknown
- [ ] Corporate Actions + News were searched through target expiry
- [ ] News-derived event dates are labeled unconfirmed
- [ ] Strategy from 25-strategy catalog; max loss stated
- [ ] All legs: OCC symbols, intents, ratios
- [ ] Options approval level sufficient
- [ ] Stock held for covered structures (if applicable)
- [ ] `alpaca doctor` passed for the chosen profile (no `-p`/`--profile` in any command)
- [ ] `options_buying_power` sufficient for proposed order
- [ ] Full CLI command(s) shown in preview, including the active profile name

---

## 3 - Source-of-truth references

| Source | URL | Used for |
|---|---|---|
| Alpaca CLI docs | https://docs.alpaca.markets/us/docs/alpacas-cli | Commands, flags |
| Corporate Actions | https://docs.alpaca.markets/us/reference/corporateactions-1 | Dividends, splits, mergers, other announced actions |
| News API | https://docs.alpaca.markets/us/reference/news-3 | Earnings/catalyst signals (not authoritative calendar dates) |
| Options trading | https://docs.alpaca.markets/us/docs/options-trading | Levels, contracts |
| Options Level 3 / mleg | https://docs.alpaca.markets/us/docs/options-level-3-trading | Multi-leg JSON |
| Options Disclosure Document | https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document | Risk disclosure |
| Alpaca disclosures | https://alpaca.markets/disclosures | Broker disclosures |

### CLI discovery rule

Your agent runs `alpaca order submit --help` before assuming flags. For `mleg`, pass the legs as a JSON array with `alpaca order submit --order-class mleg --legs` — see **Part VII**. `--dry-run` prints the exact request body without submitting; use it to build the preview.

---

## 4 - Workflow

### Phase 0: Environment and profile selection (every session)

```bash
alpaca profile list --json
```

Ask the user "paper or live?" and which listed profile to use. Set `ALPACA_PROFILE` for the session (never `-p`/`--profile` per command).

### Phase 1: Strategy confirmation

Map your intent to one of 25 strategies. Restate outlook, legs, and max loss. Wait for your confirmation.

### Phase 2: Education gate

Relevant **Part III** modules for new users or short premium.

### Phase 3: Account verification (every session)

```bash
alpaca doctor
alpaca account get --jq '{account_number, status, trading_blocked, options_approved_level, options_trading_level, options_buying_power, buying_power}'
```

Classify environment from the `alpaca doctor` `Trading:` line, not the profile name. **STOP** if this does not match what the user asked for in Phase 0.

### Phase 4: Contract discovery

```bash
alpaca data option chain --underlying-symbol AAPL
alpaca data option chain --underlying-symbol SPY --expiration-date 2026-09-19 --type call
alpaca option get --symbol-or-id AAPL250919C00210000
```

On 0DTE, Greek fields may be null when \(T - t \to 0\); use quotes from chain output.

### Phase 5: Order preview

**Single-leg:**

```bash
alpaca order submit \
  --symbol AAPL250919C00210000 \
  --qty 1 \
  --side buy \
  --type limit \
  --limit-price 3.50 \
  --time-in-force day \
  --position-intent buy_to_open \
  --client-order-id "$(uuidgen)"
```

**Multi-leg (`mleg`):**

```bash
alpaca order submit \
  --order-class mleg \
  --qty 1 \
  --type limit \
  --limit-price 0.95 \
  --time-in-force day \
  --client-order-id "$(uuidgen)" \
  --legs '[ ... ]'
```

Run the exact command with `--dry-run` first and show its request body in the preview. Show full preview table (profile, `PAPER`/`LIVE`, legs, limit, max loss), exact command, and `confirmation_mode`. On **paper**: if `on`, ask **Submit? (yes / no)**; if `off`, run after preview. On **live**: always show the real-money warning and ask the user to type the literal word `LIVE` — `confirmation_mode` does not change this.

### Phase 6: Submit and monitor

Execute after your yes (paper) or typed `LIVE` (live). Poll `alpaca order get --order-id …`. Refresh `alpaca position list`.

### Phase 7: Exercise (when needed)

```bash
alpaca option exercise --help
```

Exercise acts on all held contracts of the symbol and is irreversible — show the contract, the resulting underlying obligation, and the cash impact, and require an explicit yes regardless of `confirmation_mode` (and on live, also regardless of the typed-`LIVE` order gate). Warn about automatic ITM exercise at expiry per [Alpaca options docs](https://docs.alpaca.markets/us/docs/options-trading).

---

## 5 - Output contract

```
runs/<YYYYMMDD-HHMMSS>-options-trading-cli/
  notes.md
  raw/
    account.json
    chain.json
    order_submit.json
    order_status.json
  orders.json
  order_log.csv
  review.md
```

Save every CLI stdout/stderr to `raw/`.

---

## 6 - Execution rules

1. **Environment and profile first** — ask paper or live, list profiles with `alpaca profile list --json`, let the user pick, then show the full `account_number` and `PAPER` or `LIVE` before any other account result
2. **Outlook first** — ask investment outlook; shortlist **≥2–3** structures; **user selects** before any CLI order command
3. **No trade recommendations** — objective comparisons only; not investment advice
4. **No default environment** — never assume paper; verify the chosen profile's resolved environment matches stated intent before every submission; never pass `-p`/`--profile`
5. **All commands** — `required_permissions: ["all"]`
6. **Discover flags** — `--help` before assuming syntax
7. **JSON output** — the CLI prints JSON by default; filter with `--jq`
8. **mleg via `alpaca order submit --order-class mleg --legs`** — do not split defined spreads into naked legs without your explicit acceptance of leg risk
9. **25 strategies only** — reject excluded strategies per **Part II**
10. **Re-run Part IV** when strikes or net credit change (Module F)
11. **Automatic context** — query positions, Corporate Actions, and News before shortlisting; ask the user only on lookup failure or unresolved material timing
12. **Evidence labels** — corporate-action records may be delayed/incomplete; news-derived earnings/catalyst dates are unconfirmed

---

## 7 - Validation and tests

Before every submit, re-run the strategy confirmation checklist in §2 and the **Part IV** payoff for the quoted strikes, and compare the `--dry-run` body with the preview. After submit, confirm the order status and report rejections, partial fills, and remaining quantity.

---

## 8 - Disclosures, safety, and data handling

> Options involve significant risk and are not suitable for all investors. Read the [Options Disclosure Document](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document). Paper trading is simulated and may not reflect live fills, fees, or liquidity. **Live trading risks real money** — losses can exceed the premium paid on short-option positions. This material is not investment advice. Review [Alpaca disclosures](https://alpaca.markets/disclosures).

Your agent includes this in sessions involving order placement, and repeats the live-specific warning on every live preview. Never store API keys in run folders.

---

## 9 - Anti-patterns

- **NEVER** assume paper (or live) — ask which environment the session uses before any Alpaca call
- **NEVER** auto-select a CLI profile when more than one is configured — list them and let the user choose
- **NEVER** trust a profile's name as proof of environment — classify from `alpaca doctor`'s `Trading:` line
- **NEVER** pass `-p`/`--profile` per command — set `ALPACA_PROFILE` once for the session so the check and the order resolve to the same endpoint
- **NEVER** use account data or preview an order without showing the full `account_number` and whether the profile is `PAPER` or `LIVE`
- **NEVER** recommend a specific trade or build CLI order commands before the user selects a structure and sets execute intent
- **NEVER** shortlist fewer than 2 catalog structures when matching an outlook (unless only one valid after exclusions)
- **NEVER** ask the user for holdings before trying `alpaca position list`
- **NEVER** present Alpaca News as an authoritative earnings calendar
- **NEVER** accept "yes" (or anything other than the literal word `LIVE`) as sufficient to submit a live order
- **NEVER** let `confirmation_mode: off` bypass the typed `LIVE` confirmation on a live profile
- **NEVER** bypass CLI with raw `curl` when this is the CLI skill
- **NEVER** omit `--position-intent` on options
- **NEVER** use non-simplified `ratio_qty` in mleg JSON
- **NEVER** combine stock + options in one mleg payload
- **NEVER** invent legs outside **Part II**
- **NEVER** proceed after `alpaca doctor` fails
- **NEVER** apply equity catalog strategies to index options (SPX, etc.) without Alpaca index docs
- **NEVER** exercise an option without explicit confirmation, regardless of `confirmation_mode`

---

## 10 - Related content in this file

| Part | Section | Contents |
|---|---|---|
| **I** | §0–§9 above | CLI workflow, environment/profile selection, command patterns |
| **II** | Strategy Catalog | All 25 strategies |
| **III** | Education Modules | Modules A–K |
| **IV** | Payoff Calculator | Breakeven engine (#1–25) |
| **V** | Strategy Comparison | Outlook map and side-by-side workflow |
| **VI** | Examples | CLI end-to-end examples |
| **VII** | CLI Command Reference | Chain, orders, mleg, exercise, idempotency |

### Companion skills

| Skill | Description |
|---|---|
| `alpaca-trading-options-trading-mcp` | MCP execution version |
| `alpaca-trading-paper-trading-cli` | Dedicated paper-only equity/crypto CLI workflow — hard-blocks live |
| `alpaca-trading-backtest` | Historical signals |

---

# Part II — Strategy Catalog (25)

Alpaca execution mapping for each strategy. Definitions align with standard retail options education and the curated set in this skill.

**Asset scope:** US listed **equity and ETF** options (American-style, 100-share multiplier). Index options (SPX, etc.) are a separate Alpaca product — not mapped to this catalog (see education Module K).

**Alpaca constraints**

- Multi-leg orders: `order_class: mleg`, **2–4 legs**, no equity leg in the same order
- `ratio_qty` values must be in simplest form (GCD = 1)
- Contract multiplier: **100 shares** per contract
- See **Part VII** for `mleg` command templates and **Part III** Module D for **0DTE Greeks** (Black–Scholes when \(T - t \to 0\))
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
| **Alpaca** | Stock + 3-leg `mleg`; L3 |
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
3. **Stock repair** — long underwater stock + buy 1 ATM call + sell 2 OTM calls. Attempts to recover basis without adding cash to the stock; max outcome capped by short calls.

**Your agent should:** Map these to `mleg` with simplified ratios (GCD = 1); show max loss before submit. For stock repair, verify stock is already held.

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

1. **Choose the environment first** — your agent asks paper or live before any Alpaca call; it does not default to paper. It then lists CLI profiles with `alpaca profile list --json`, lets you pick one, and shows the full `account_number` plus `PAPER` or `LIVE`, classified from `alpaca doctor`'s `Trading:` line. Repeat both in every order preview. Stop on a mismatch between stated and verified environment.
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
| **Execute** | Full workflow after **your** structure selection + environment/profile verification in §0 Steps 1–2; paper uses `confirmation_mode`, live always requires typed `LIVE` |

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
| **Breakeven @ expiry** | \(B + N\) (approximate; verify with payoff table) |

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

**Inputs:** Long far leg (\(K_l\), \(D_l\)), short near leg (\(K_s\), \(C_s\)); net \(N = D_l - C_s\)

Same as calendar: **multi-expiry** — run payoff table at **near expiry** with stated assumptions for the remaining long leg (mark at intrinsic or quote).

---

### #15 — Long straddle

**Inputs:** Strike \(K\), total debit \(D = D_{\text{call}} + D_{\text{put}}\)

| Max loss | \(D\) (at \(S = K\)) |
| Max profit | Unlimited both tails |
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
| 14 | Diagonal | \(\approx N\) | Table |
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
| 7 | Put spread collar | Cheaper protect | 30–90 | Mixed | Capped | Floored, then stock ↓ below short put | 1 | Yes | L3 | 3 opt |
| 8 | Covered strangle | Neutral income | 30–45 | Credit | Capped @ call | Stock + put ↓ | 1 | Yes | L3 | 2 opt |
| 9 | Bull call spread | Mod bull | 30–60 | Debit | Width − debit | Debit | 1 | No | L3 | 2 |
| 10 | Bear call spread | Bear–neutral | 30–45 | Credit | Credit | Width − credit | 1 | No | L3 | 2 |
| 11 | Bull put spread | Bull–neutral | 30–45 | Credit | Credit | Width − credit | 1 | No | L3 | 2 |
| 12 | Bear put spread | Bearish | 30–60 | Debit | Width − debit | Debit | 1 | No | L3 | 2 |
| 13 | Long calendar | Neutral near | Near + far | Debit | Variable | ≈ debit | Table | No | L3 | 2 |
| 14 | Diagonal | Mild bias | Near + far | Mixed | Variable | ≈ net debit | Table | No | L3 | 2 |
| 15 | Long straddle | Vol ↑ | 7–45 | Debit | Unlimited tails | Total prem | 2 | No | L3 | 2 |
| 16 | Long strangle | Vol ↑ cheap | 7–45 | Debit | Unlimited tails | Total prem | 2 | No | L3 | 2 |
| 17 | Iron condor | Range | 30–45 | Credit | Credit | Wing − credit | 2 | No | L3 | 4 |
| 18 | Iron butterfly | Pin | 30–45 | Credit | Credit | Wing − credit | 2 | No | L3 | 4 |
| 19 | Long call fly | Pin (calls) | 30–45 | Debit | Wing − debit | Debit | 2 | No | L3 | 3 |
| 20 | Long put fly | Pin (puts) | 30–45 | Debit | Wing − debit | Debit | 2 | No | L3 | 3 |
| 21 | Wheel | Income cycle | 30–45 | Credit | Premium steps | CSP max loss | Per leg | Optional | L1 | seq |
| 22 | PMCC | Bull LEAP | LEAP + short | Mixed | Capped | LEAP cost | Table | No | L2+ | 2 |
| 23 | Call backspread | Convex bull | 45–90 | Debit/cred | Unlimited ↑ | Zone loss | 1–2 | No | L3 | 2 |
| 24 | Put backspread | Convex bear | 45–90 | Debit/cred | Large ↓ | Zone loss | 1–2 | No | L3 | 2 |
| 25 | Stock repair | Repair basis | 60–180 | Mixed | Capped ↑ | Tail ↓ | Table | Yes | L3 | 3 opt |

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

CLI end-to-end patterns. Discover flags with `--help` on your installed version.

**Pattern:** Ask paper or live → pick profile → ask outlook → shortlist **≥2–3** structures → **user selects** → CLI order commands only when asked.

---

## Example -1 — Choosing paper vs live and picking a profile

**User:** Help me trade options on AAPL.

**Agent:**

1. Ask: "Paper or live trading for this session?"
2. List profiles:

```bash
alpaca profile list --json
```

3. User picks a profile (e.g., `paper` after stating paper). Set `export ALPACA_PROFILE=paper` for the session — never `-p`/`--profile`.
4. Verify:

```bash
alpaca doctor    # classify PAPER/LIVE from Trading: line
alpaca account get --jq '.account_number'
```

5. Show full `account_number` and `PAPER` or `LIVE`. **STOP** if the verified environment disagrees with Step 1.

---

## Example 0 — Outlook first (no CLI order)

**User:** What options play makes sense on NVDA?

**Agent:** After Example -1 environment/profile selection: ask direction, DTE, and max loss. Then run `alpaca position list`, `alpaca data corporate-actions`, and `alpaca data news` through target expiry. Label news-derived dates unconfirmed. Shortlist ≥2 from **Part V** (e.g., #9 bull call, #11 bull put, #4 CSP). **User picks** before any `alpaca order submit`.

---

## Example 1 — Reject short strangle

**User:** Sell a TSLA strangle for premium.

**Agent:** Strategy excluded (undefined risk). Shortlist supported alternatives: iron condor (#17) **and** bull put spread (#11). **User selects** — no recommendation.

---

## Example 2 — Iron condor on paper (after user selects #17)

**User:** Neutral on SPY — show structures. *(Agent shortlists ≥2.)* **User:** Paper trade the iron condor (#17).

**Agent:**

1. Confirm user selected strategy #17 and re-verify the paper profile (`alpaca doctor` → `PAPER`).
2. Chain:

```bash
alpaca data option chain --underlying-symbol SPY --expiration-date-gte 2026-09-01 --expiration-date-lte 2026-10-31
```

3. Preview: `--dry-run` request body + max loss + profile + `PAPER`.
4. On yes (paper, `confirmation_mode: on`):

```bash
alpaca order submit --order-class mleg --qty 1 --type limit --limit-price 1.80 --time-in-force day --legs '[ ... 4 legs ... ]'
```

5. Monitor: `alpaca order get --order-id …`

---

## Example 3 — Cash-secured put (wheel step 1)

```bash
alpaca order submit \
  --symbol AAPL251017P00210000 \
  --qty 1 \
  --side sell \
  --type limit \
  --limit-price 3.20 \
  --time-in-force day \
  --position-intent sell_to_open \
  --client-order-id "$(uuidgen)"
```

---

## Example 4 — Protective put (stock already held)

```bash
alpaca position get --symbol-or-asset-id AAPL
alpaca order submit \
  --symbol AAPL251017P00200000 \
  --qty 1 \
  --side buy \
  --type limit \
  --limit-price 2.50 \
  --time-in-force day \
  --position-intent buy_to_open \
  --client-order-id "$(uuidgen)"
```

---

## Example 5 — Bull call spread

```bash
alpaca order submit \
  --order-class mleg \
  --qty 1 \
  --type limit \
  --limit-price 0.95 \
  --time-in-force day \
  --client-order-id "$(uuidgen)" \
  --legs '[
    {"symbol": "AAPL251017C00210000", "ratio_qty": "1", "side": "buy", "position_intent": "buy_to_open"},
    {"symbol": "AAPL251017C00220000", "ratio_qty": "1", "side": "sell", "position_intent": "sell_to_open"}
  ]'
```

---

## Example 6 — Auto-submit (`confirmation_mode: off`) on paper

**User:** Paper bull put spread on AAPL; don't ask me to confirm each order.

**Agent:**

1. Confirm environment is paper and profile still resolves to paper via `alpaca doctor`.
2. Set `confirmation_mode: off`.
3. Run payoff + preview table (max loss, legs, CLI command, `--dry-run` body, profile, `PAPER`).
4. Log `confirmation_mode: off` in `notes.md`.
5. Execute `alpaca order submit --order-class mleg ... --legs '[ ... ]'` without yes/no prompt.
6. Monitor with `alpaca order get --order-id …`.

---

## Example 7 — Live order requires typing `LIVE`, even with `confirmation_mode: off`

**User:** Live trade the previewed iron condor. Don't ask me to confirm — `confirmation_mode: off`.

**Agent:**

1. Confirm environment is live and profile resolves to `https://api.alpaca.markets`.
2. Show preview with real-money warning, profile, `LIVE`, max loss, and `--dry-run` body.
3. User replies "yes" → **reject**. Require the literal word `LIVE`.
4. User types `LIVE` → submit. `confirmation_mode: off` does not skip this gate.

---

# Part VII — CLI Command Reference

Quick reference for options workflows via the Alpaca CLI. Always run `--help` on the installed version before assuming flags.

All commands require `required_permissions: ["all"]`. Output is JSON by default; filter with `--jq`. Never pass `-p`/`--profile` — set `ALPACA_PROFILE` for the session instead.

---

## Session setup

```bash
alpaca version
alpaca profile list --json
# Ask paper or live; user picks a profile; then:
export ALPACA_PROFILE=<chosen-profile>   # never -p/--profile per command
alpaca doctor    # classify PAPER/LIVE from Trading: line; must match stated intent
alpaca account get --jq '{account_number, status, buying_power, options_trading_level, options_buying_power, equity}'
alpaca clock
```

### Profile & environment selection

- List: `alpaca profile list --json`
- Activate for the session: `export ALPACA_PROFILE=<name>` — **never** `-p`/`--profile` on individual commands (`alpaca doctor` ignores `-p`)
- Classify environment from `alpaca doctor`'s `Trading:` line:
  - `https://paper-api.alpaca.markets` → `PAPER`
  - `https://api.alpaca.markets` → `LIVE`
- Gotcha: a profile named "paper" can still resolve to live if `ALPACA_LIVE_TRADE=true` is exported — always trust `alpaca doctor`, not the profile name

---

## Option chain & contracts

```bash
# Full chain with quotes and Greeks (paginate with --page-token)
alpaca data option chain --underlying-symbol AAPL

# Filtered chain
alpaca data option chain \
  --underlying-symbol SPY \
  --expiration-date 2026-09-19 \
  --type put \
  --strike-price-gte 540 \
  --strike-price-lte 560

# Expiry window
alpaca data option chain --underlying-symbol AAPL --expiration-date-gte 2026-09-01 --expiration-date-lte 2026-12-31

# Single contract details
alpaca option get --symbol-or-id AAPL250919C00210000
```

---

## Positions (stock + options)

```bash
alpaca position list
alpaca position get --symbol-or-asset-id AAPL
alpaca position get --symbol-or-asset-id AAPL250919C00210000
```

Use before covered call, collar, covered strangle, wheel.

---

## Upcoming events (before structure shortlist)

Use the installed CLI as the source of truth for flags:

```bash
alpaca data corporate-actions --help
alpaca data corporate-actions --schema
alpaca data news --help
alpaca data news --schema

# Illustrative — adapt date flags from --help
alpaca data corporate-actions \
  --symbols AAPL \
  --start 2026-10-11 \
  --end 2027-01-09 \
  --data-quality all

alpaca data news \
  --symbols AAPL \
  --start 2026-10-11 \
  --end 2027-01-09
```

`alpaca data corporate-actions` wraps Alpaca's [`GET /v1/corporate-actions`](https://docs.alpaca.markets/us/reference/corporateactions-1). Follow `next_page_token` until exhausted. Inspect all returned action types, including dividends, splits, mergers, spin-offs, reorganizations, and redemptions. Results can be delayed or incomplete; an empty response does not prove no event exists.

Alpaca has **no dedicated earnings-calendar endpoint**. Search News for earnings and catalysts, but cite the article and label extracted future dates **unconfirmed / news-derived**. Ask the user only when timing remains material and unresolved.

---

## Single-leg option orders

```bash
alpaca order submit --help

# Buy to open — long call
alpaca order submit \
  --symbol AAPL250919C00210000 \
  --qty 1 \
  --side buy \
  --type limit \
  --limit-price 4.25 \
  --time-in-force day \
  --position-intent buy_to_open \
  --client-order-id "$(uuidgen)"

# Sell to open — cash-secured put
alpaca order submit \
  --symbol AAPL250919P00200000 \
  --qty 1 \
  --side sell \
  --type limit \
  --limit-price 2.10 \
  --time-in-force day \
  --position-intent sell_to_open \
  --client-order-id "$(uuidgen)"

# Sell to close
alpaca order submit \
  --symbol AAPL250919C00210000 \
  --qty 1 \
  --side sell \
  --type limit \
  --limit-price 5.00 \
  --time-in-force day \
  --position-intent sell_to_close \
  --client-order-id "$(uuidgen)"
```

---

## Multi-leg (`mleg`)

`alpaca order submit --order-class mleg` takes the legs as a JSON array in `--legs` (up to 4). Omit `--symbol`, `--side`, and `--position-intent` at the top level — each leg carries its own. Add `--dry-run` to print the request body without submitting.

```bash
# Iron condor (4 legs)
alpaca order submit \
  --order-class mleg \
  --qty 1 \
  --type limit \
  --limit-price 1.80 \
  --time-in-force day \
  --client-order-id "ic-spy-cli-001" \
  --legs '[
    {"symbol": "SPY250919P00550000", "ratio_qty": "1", "side": "buy", "position_intent": "buy_to_open"},
    {"symbol": "SPY250919P00555000", "ratio_qty": "1", "side": "sell", "position_intent": "sell_to_open"},
    {"symbol": "SPY250919C00565000", "ratio_qty": "1", "side": "sell", "position_intent": "sell_to_open"},
    {"symbol": "SPY250919C00570000", "ratio_qty": "1", "side": "buy", "position_intent": "buy_to_open"}
  ]'

# Bull call spread (2 legs)
alpaca order submit \
  --order-class mleg \
  --qty 1 \
  --type limit \
  --limit-price 1.00 \
  --time-in-force day \
  --client-order-id "$(uuidgen)" \
  --legs '[
    {"symbol": "AAPL250919C00190000", "ratio_qty": "1", "side": "buy", "position_intent": "buy_to_open"},
    {"symbol": "AAPL250919C00210000", "ratio_qty": "1", "side": "sell", "position_intent": "sell_to_open"}
  ]'

# Long call butterfly (1:2:1)
alpaca order submit \
  --order-class mleg \
  --qty 1 \
  --type limit \
  --limit-price 0.45 \
  --time-in-force day \
  --client-order-id "$(uuidgen)" \
  --legs '[
    {"symbol": "SPY250919C00560000", "ratio_qty": "1", "side": "buy", "position_intent": "buy_to_open"},
    {"symbol": "SPY250919C00565000", "ratio_qty": "2", "side": "sell", "position_intent": "sell_to_open"},
    {"symbol": "SPY250919C00570000", "ratio_qty": "1", "side": "buy", "position_intent": "buy_to_open"}
  ]'
```

Use heredocs in scripts for readable JSON:

```bash
read -r -d '' LEGS <<'EOF'
[
  {"symbol": "SPY250919P00550000", "ratio_qty": "1", "side": "buy", "position_intent": "buy_to_open"},
  {"symbol": "SPY250919P00555000", "ratio_qty": "1", "side": "sell", "position_intent": "sell_to_open"}
]
EOF
alpaca order submit --order-class mleg --qty 1 --type limit --limit-price 1.80 --time-in-force day --legs "$LEGS" --dry-run
```

---

## Order management

```bash
alpaca order get --order-id {id}
alpaca order list --status open
alpaca order cancel --order-id {id}
alpaca order replace --order-id {id} --limit-price 1.75
```

---

## Exercise

Irreversible, and exercises **all** held contracts of the symbol. Require an explicit yes regardless of `confirmation_mode`.

```bash
alpaca option exercise --symbol-or-contract-id AAPL250919C00210000
```

---

## Contracts (alternative to chain, no quotes)

```bash
alpaca option contracts --underlying-symbols AAPL --expiration-date-gte 2026-09-01 --limit 100
```

---

## Idempotency

Always set `--client-order-id` on submissions. On failure, query before retry:

```bash
alpaca order get-by-client-id --client-order-id {uuid}
```
