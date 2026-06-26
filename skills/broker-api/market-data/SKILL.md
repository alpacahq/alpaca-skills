---
name: alpaca-broker-market-data
description: Pull and stream US stock market data from Alpaca — REST snapshots/bars/trades/quotes, historical bars with timeframes and feeds (IEX vs SIP), the assets master list, market clock & calendar, news, and the real-time WebSocket stream. Use when building charts, quotes, price feeds, or asset metadata on Alpaca in any language.
---

# Alpaca Market Data API — Stocks (REST + WebSocket)

Real-time and historical US equity data. Unlike the Broker endpoints, market data lives on **its own host with its own auth**, and the real-time feed is **WebSocket**, not SSE.

> Read `alpaca-broker-integration` first. Assets/clock/calendar live on the **Trading API** host; everything else here is the **Market Data API** host.

## Reference
- Guides: `https://docs.alpaca.markets/docs/historical-stock-data`, `https://docs.alpaca.markets/docs/streaming-market-data`
- Live schema: `alpaca-docs` MCP → `list-endpoints` title `"Market Data API"`

## 0. Hosts & auth

| Surface | Host |
|---------|------|
| Market data REST | `https://data.alpaca.markets` (sandbox `data.sandbox.alpaca.markets`) |
| Market data WebSocket | `wss://stream.data.alpaca.markets/{version}/{feed}` |
| Assets / clock / calendar | `https://api.alpaca.markets` (Trading API) — paper: `paper-api.alpaca.markets` |

**Auth:** headers `APCA-API-KEY-ID` / `APCA-API-SECRET-KEY` (Broker partners may use Broker Basic auth in broker context).

## 1. REST endpoints

| Path | Purpose |
|------|---------|
| `GET /v2/stocks/snapshots?symbols=…` · `GET /v2/stocks/{symbol}/snapshot` | Snapshot (latest trade/quote + bars) |
| `GET /v2/stocks/bars?symbols=…` · `GET /v2/stocks/{symbol}/bars` | Historical OHLCV bars |
| `GET /v2/stocks/bars/latest` · `…/{symbol}/bars/latest` | Latest bar(s) |
| `GET /v2/stocks/trades[/latest]` · `GET /v2/stocks/quotes[/latest]` | Historical / latest trades & quotes |
| `GET /v2/stocks/auctions` | Opening/closing auctions |
| `GET /v2/stocks/meta/conditions/{trade\|quote}` · `/meta/exchanges` | Code lookups |
| `GET /v1beta1/news?symbols=…` | News (max `limit` 50) |
| `GET /v1beta1/screener/stocks/most-actives` · `/screener/{stocks\|crypto}/movers` | Screeners |
| `GET /v2/assets` *(Trading API host)* · `GET /v1/assets` *(Broker API host)* | Asset master / tradability |
| `GET /v2/clock` · `GET /v2/calendar` *(Trading API host)* | Market hours |

> **Clock/calendar/assets paths are host-dependent — verified live against the sandbox:**
>
> | Path | Trading API host (`api.alpaca.markets`) | Broker API host (`broker-api.*`) |
> |------|:--:|:--:|
> | `/v1/clock` | — | **200** |
> | `/v2/clock` | **200** | **200** |
> | `/v1/calendar` | — | **200** |
> | `/v2/calendar` | **200** | **404** |
> | `/v1/assets` | — | **200** |
> | `/v2/assets` | **200** | **404** |
>
> So: on the **Trading/Market-Data API host** use `/v2/clock`, `/v2/calendar`, `/v2/assets`. On the **Broker API host** use **`/v1/clock`**, **`/v1/calendar`**, **`/v1/assets`** (`/v1/clock` and `/v2/clock` both work there; `/v2/calendar` and `/v2/assets` 404). A Broker-API integration hitting `/v1/clock` is **correct**, not stale.

## 2. Bars — params

| Param | Notes |
|-------|-------|
| `timeframe` | `[1-59]Min`/`T`, `[1-23]Hour`/`H`, `1Day`/`D`, `1Week`/`W`, `[1,2,3,4,6,12]Month`/`M`. Case-sensitive. e.g. `1Min`, `5Min`, `1Hour`, `1Day` |
| `start` / `end` | RFC3339 or `YYYY-MM-DD`, inclusive |
| `limit` | default **1000**, max **10000** — counts data points **across all symbols**, not per symbol |
| `page_token` | pagination cursor (from `next_page_token`) |
| `adjustment` | `raw` (default), `split`, `dividend`, `spin-off`, `all` — comma-combinable |
| `feed` | see §3 |
| `sort` | `asc` (default) / `desc` |
| `asof` | `YYYY-MM-DD` for symbol/name-change mapping; `-` skips mapping |

**Pagination lesson:** results are sorted by **symbol, then timestamp**. A multi-symbol request that hits `limit` may return only the first symbol(s) — you must follow `next_page_token` until empty to get them all. Don't assume one page = all symbols.

## 3. Feeds (entitlement matters)

- `iex` — single exchange (~2.5% of volume). **The only feed available without a paid subscription.** Good for dev/testing.
- `sip` — consolidated, all exchanges (100% volume). **Requires a paid data plan.**
- `delayed_sip` — SIP delayed 15 min (latest/snapshot endpoints).
- `otc`, `boats` (Blue Ocean overnight ATS), `overnight` (Alpaca-derived, cheaper).

**Lessons:**
- **Pick `iex` explicitly** if you're on the free tier — some endpoints default to `sip`, which then 403s without entitlement. (A common surprise: "why is my historical request failing?" → defaulted to SIP.)
- Without real-time access, `start`/`end` windows **withhold the most recent 15 minutes**.
- Trade/quote **sizes are in shares** as of 2025-11-03 (were round lots before).

## 4. Object shapes (compact keys)

**Snapshot** per symbol: `latestTrade`, `latestQuote`, `minuteBar`, `dailyBar`, `prevDailyBar`. Multi-symbol response is a map `{ "AAPL": {…} }`.

- **Bar:** `t` time, `o` open, `h` high, `l` low, `c` close, `v` volume, `n` trade count, `vw` VWAP.
- **Trade:** `t` time, `p` price, `s` size, `x` exchange, `c` conditions, `z` tape, `i` id.
- **Quote:** `bp`/`bs`/`bx` bid price/size/exchange, `ap`/`as`/`ax` ask price/size/exchange, `c` conditions, `z` tape. (price `0` = no active bid/ask.)

## 5. WebSocket protocol

**URL:** `wss://stream.data.alpaca.markets/{version}/{feed}` — e.g. `v2/iex`, `v2/sip`, `v2/delayed_sip`, `v1beta1/boats`, `v1beta1/overnight`, or `v2/test` (always-on, use symbol `FAKEPACA`).

**Connect flow:**
1. Connect → `[{"T":"success","msg":"connected"}]`
2. **Auth within 10s:** `{"action":"auth","key":"…","secret":"…"}` → `[{"T":"success","msg":"authenticated"}]`
3. Subscribe: `{"action":"subscribe","trades":["AAPL"],"quotes":["AMD"],"bars":["*"]}` → server echoes full subscription state. `*` = all symbols. `unsubscribe` removes.

**Message types** (every message is a **JSON array**; `T` discriminates): `t` trade, `q` quote, `b` minute bar, `d` daily bar, `u` updated bar, `s` trading status (halt/resume), `l` LULD, `c` correction, `x` cancel/error, `i` imbalance; control: `success`, `error`, `subscription`. Subscribing to `trades` auto-adds `corrections` + `cancelErrors`.

**WebSocket lessons:**
- **One concurrent connection per key** on most plans — a 2nd connection → `{"code":406,"connection limit exceeded"}`. Centralize the stream in **one process** and fan out to your own clients (don't open a socket per user).
- Authenticate within **10s** or get dropped (`404`).
- Other error codes: `401` not auth'd, `402` auth failed, `405` symbol limit, `407` slow client, `409` insufficient subscription (feed not entitled), `410` invalid action for feed.
- Messages are **batched** — always iterate the array; don't assume one frame = one event.
- Handle **`u` (updated bar)** and **`c`/`x` (corrections/cancels)**: a streamed bar/trade can be revised after the fact.

## 6. Assets, clock, calendar

Use the host-appropriate path (see the table in §1): `/v2/...` on the Trading API host, `/v1/...` on the Broker API host.

- **Assets** (`GET /v2/assets` on Trading host · `GET /v1/assets` and `/v1/assets/{symbol}` on Broker host) — tradability metadata: `tradable`, `fractionable`, `marginable`, `shortable`, `borrow_status` (replaces deprecated `easy_to_borrow`), `status` (`active`/`inactive`), `class` (`us_equity`/`us_option`/`crypto`/`ipo`), `exchange`, `attributes[]` (e.g. `has_options`, `overnight_tradable`). Filter by `status`, `asset_class`, `exchange`. **Cache this** — it changes slowly; query it before trading to confirm `tradable`/`fractionable` (see `alpaca-broker-trading-orders`).
- **Clock** (`/v2/clock` on Trading host · `/v1/clock` on Broker host) — `is_open`, `next_open`, `next_close`, `timestamp`. Use this to gate market-hours logic instead of hardcoding 9:30–16:00 ET.
- **Calendar** (`/v2/calendar` on Trading host · `/v1/calendar` on Broker host — note there is no `/v2/calendar` on the Broker host) — per-day `open`/`close` (`HH:MM`), `session_open`/`session_close` (`HHMM`, extended hours), `settlement_date`. **Use the calendar for holidays** — a naive "weekdays only" check runs jobs on market holidays (harmless but wasteful) and miscomputes "previous trading day."

## 7. Caching strategy (cost & rate-limit lesson)

Market data is the highest-volume, highest-cost surface. Production lesson:
1. **Persist historical bars** in your own store keyed by `(symbol, timeframe, timestamp)` with upsert/skip-duplicate, and serve charts from there — only fetch the gap from Alpaca.
2. **Cache snapshots/quotes** in a short-TTL cache (TTL tuned to market-open vs closed).
3. **Run one bulk backfill job** for searchable symbols on a schedule rather than fetching per user request.
4. Always follow `next_page_token` and watch `X-RateLimit-Remaining` (see `alpaca-broker-rate-limits-resilience`).

**Related skills:** tradability before ordering → `alpaca-broker-trading-orders`; rate limits/pagination → `alpaca-broker-rate-limits-resilience`; the *broker* event stream (SSE, different from this WS) → `alpaca-broker-sse-events`.
