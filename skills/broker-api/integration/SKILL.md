---
name: alpaca-broker-integration
description: Entry point for integrating with the Alpaca Broker API (plus Market Data and Trading APIs) in any programming language. Use when a developer wants to build on Alpaca — open brokerage accounts, run KYC, fund accounts, move money via journals, place orders, consume real-time event streams, or pull market data — and need to know base URLs, auth, conventions, or which focused sub-skill to use.
---

# Alpaca Integration Assistant

You are an expert on the **Alpaca** APIs. Help developers integrate with Alpaca in **any programming language**. Generate working code, explain protocols, and debug integration issues.

This is the **router / overview** skill. It covers the things that are true across *all* of Alpaca's APIs — the API families, base URLs, auth, consumption styles, and wire conventions — and points you to a focused sub-skill for each domain. Read this first, then jump to the specific skill for the task.

> Most of the hard-won value in these skills is in the **lessons-learned** sub-skills (reconciliation, rate limits, money precision, SSE reliability). Alpaca's reference docs tell you *what* the endpoints are; these skills tell you *what breaks in production and why*.

---

## Reference Documentation

- Docs home: `https://docs.alpaca.markets/`
- API reference: `https://docs.alpaca.markets/reference/`
- Machine-readable index: `https://docs.alpaca.markets/us/llms.txt` (the root `llms.txt` is the India/GIFT City index; `llms-full.txt` redirects to the docs home)
- OpenAPI specs (4): **Authentication API**, **Broker API**, **Market Data API**, **Trading API**

**Live schema lookups:** if the `alpaca-docs` MCP server is connected, prefer it over guessing — `list-specs`, `list-endpoints`, `get-endpoint` (exact request/response schemas + servers), and `search` / `fetch` (guide pages). Always confirm an exact payload against the spec before generating code that posts money or orders.

---

## 1. The four API families

| Family | What it's for | Who uses it |
|--------|---------------|-------------|
| **Broker API** | Open & manage brokerage accounts on behalf of *your* end users (KYC, funding, journals, trading-for-accounts, documents, events). You are the broker-of-record's tech partner; you custody many sub-accounts under your firm. | Apps that onboard their own users and hold their assets (neobrokers, fintechs). |
| **Trading API** | Trade a *single* account that belongs to the API-key holder. | Individual algo traders, bots. |
| **Market Data API** | Real-time + historical prices, bars, quotes, trades, news, corporate actions, screener. REST and WebSocket. | Everyone. |
| **Authentication API** | Issues access tokens: `client_credentials` for your own machine-to-machine calls, plus OAuth 2.0 flows for letting third parties act on an Alpaca account. | Every Broker partner; OAuth integrations. |

**Decide first which family you're on — it changes the base URL, the auth, and the URL shape of every call.** The most common confusion: Broker API places orders at `/v1/trading/accounts/{account_id}/orders` (the account is in the path because you act *for* a user), whereas the standalone Trading API places orders at `/v2/orders` (implicitly *your own* account).

These skills focus primarily on the **Broker API**, because that's where the lifecycle is hardest: onboarding, funding rails, journals, and event reconciliation.

---

## 2. Base URLs

| Family | Production | Sandbox / Paper |
|--------|-----------|-----------------|
| **Broker API** | `https://broker-api.alpaca.markets` | `https://broker-api.sandbox.alpaca.markets` |
| **Trading API** | `https://api.alpaca.markets` | `https://paper-api.alpaca.markets` (paper) |
| **Market Data (REST)** | `https://data.alpaca.markets` | `https://data.sandbox.alpaca.markets` |
| **Market Data (WebSocket)** | `wss://stream.data.alpaca.markets` | `wss://stream.data.sandbox.alpaca.markets` |

**Always start in sandbox.** Switch by environment variable, never by code path — a single `ENV` flag that selects the base URL is the pattern that survives. Sandbox accounts can be funded with fake money and auto-approved, so you can exercise the full lifecycle without real KYC or cash.

---

## 3. Authentication

### Client credentials → Bearer token (Broker API, and Broker partners calling Market Data)

```
POST https://authx.alpaca.markets/v1/oauth2/token
     (sandbox: https://authx.sandbox.alpaca.markets/v1/oauth2/token)
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=<CLIENT_ID>&client_secret=<CLIENT_SECRET>
```

The secret goes in the **body** (`client_secret_post`), not in an `Authorization` header. The response is `{"access_token": "…", "expires_in": 899, "token_type": "Bearer"}` — tokens are valid **15 minutes**. Send it as `Authorization: Bearer <token>`.

Documented for the Broker API, and for Broker partners calling Market Data over both REST and WebSocket. On the WebSocket the auth message uses the literal key `access_token`:
```json
{"action": "auth", "key": "access_token", "secret": "<ACCESS_TOKEN>"}
```
Not yet available for the Trading API.

**Cache the token per process and refresh before expiry** — around 12 of the 15 minutes. Hold it behind one accessor that can refresh, not a startup constant. Treat a `401` on a long-lived call as *refresh and retry once* before treating it as bad credentials; whether an already-open SSE stream survives token expiry is not documented.

### Legacy key/secret → still supported, and the only path for Trading API

```
APCA-API-KEY-ID: <API_KEY_ID>
APCA-API-SECRET-KEY: <API_SECRET_KEY>
```

Broker also accepts `Authorization: Basic base64("<API_KEY_ID>:<API_SECRET_KEY>")` on REST and SSE. The Trading API uses the `APCA-API-*` headers only. For the WebSocket data stream you don't use headers — you send an auth message *after* connecting:
```json
{"action": "auth", "key": "<API_KEY_ID>", "secret": "<API_SECRET_KEY>"}
```

> Pick one scheme per client and be consistent; mixing them is a frequent source of 401s.

---

## 4. Three consumption styles

Alpaca gives you three transports. Use the right one for the job — and know that they have **different auth and different reliability characteristics**.

| Style | Transport | Use for | Skill |
|-------|-----------|---------|-------|
| **REST** | HTTPS request/response | Everything transactional: create account, fund, journal, place order, query state. | the domain skills |
| **SSE** | `text/event-stream` over a long-lived HTTPS GET | Broker lifecycle events: account status, journals, transfers, trades, non-trade activities. **Replayable** via cursors. | `alpaca-broker-sse-events` |
| **WebSocket** | `wss://` | Real-time market data (trades/quotes/bars). | `alpaca-broker-market-data` |

**Key distinction:** Broker *events* come over **SSE** (simple HTTP, replayable with `since` or `since_ulid`/`until_ulid` on v1 and `since_id` — a ULID — on v2; the v1 integer `since_id`/`until_id` are deprecated, select partners only, sunset 2027-02-15). Market *data* comes over **WebSocket** (subscribe model, auth message, ping/pong). They are different endpoints with different auth — don't conflate them.

---

## 5. Wire conventions (true across the platform)

These apply everywhere and are the source of most subtle bugs:

- **Numbers are strings.** Prices, quantities, notional, and money amounts come back as JSON strings (`"100.50"`, `"1.5"`). Parse into a decimal type, never a binary float. See `alpaca-broker-money-precision`.
- **IDs:** `account_id`, `order_id`, `journal_id`, `transfer_id` are UUIDs. Activity IDs are `<timestamp>::<uuid>` strings (e.g. `20220208125959696::88b5f678-…`) — sortable, but not ULIDs. Newer event IDs (`event_ulid` on v1, `event_id` on v2) *are* **ULIDs**, which matters for event ordering and replay cursors.
- **Idempotency:** pass your own `client_order_id` on orders so retries don't double-fill. Records you create from events should be keyed on the Alpaca ID with upsert/skip-duplicate semantics. See `alpaca-broker-reconciliation-idempotency`.
- **Pagination:** list endpoints page forward with a token. Market-data bars return `next_page_token` in the body; loop until it's empty. Activities send **no** token anywhere — on both Broker `/v1/accounts/activities` and Trading `/v2/account/activities` you pass the **`id` of the last activity in the page** as the `page_token` query param, and loop until a page comes back short or empty.
- **Rate limits:** responses carry `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` (unix seconds). On HTTP `429`, wait until reset before retrying. See `alpaca-broker-rate-limits-resilience`.
- **Timestamps:** RFC3339 (e.g. `2026-01-02T15:04:05Z`). SSE `since`/`until` accept RFC3339, but `+` in a timezone offset must be URL-encoded as `%2B`.
- **Status ≠ done.** Almost every write (account, journal, transfer, order) is asynchronous and moves through a **state machine**. A `200` means "accepted," not "settled." Always reconcile on the terminal status, which arrives later via event or poll.

---

## 6. Sandbox-first workflow

When helping someone start from zero, walk them through this order:

1. **Pick sandbox URLs** via an `ENV` switch.
2. **Authenticate** with a client-credentials Bearer token (Broker) — verify with `GET /v1/accounts` (list).
3. **Create an account** with full KYC payload → `alpaca-broker-account-onboarding`.
4. **Wait for `ACTIVE`** status (via SSE account-status events or polling) before any money/trade op.
5. **Fund it** (sandbox lets you simulate deposits) → `alpaca-broker-funding-transfers`.
6. **Move cash where it's needed** with journals → `alpaca-broker-journals`.
7. **Place an order** → `alpaca-broker-trading-orders`.
8. **Subscribe to events** to track fills/transfers in real time → `alpaca-broker-sse-events`.
9. **Add a reconciliation pass** before going live → `alpaca-broker-reconciliation-idempotency`.

---

## 7. Skill map — where to go next

| If the task is about… | Use skill |
|-----------------------|-----------|
| Creating accounts, KYC, CIP, document upload, agreements, account status, W-8BEN | **`alpaca-broker-account-onboarding`** |
| ACH / wire / funding-wallet rails, deposits, withdrawals, transfer status, the omnibus/float-account model | **`alpaca-broker-funding-transfers`** |
| Moving cash (JNLC) or shares (JNLS) between accounts, batch & reverse-batch, journal lifecycle | **`alpaca-broker-journals`** |
| Placing/canceling orders, qty vs notional, fractional shares, order lifecycle, positions, recurring buys | **`alpaca-broker-trading-orders`** |
| Snapshots, bars, quotes, assets, news, market clock/calendar, feeds (IEX/SIP), WebSocket price streams | **`alpaca-broker-market-data`** |
| Consuming Broker SSE event streams reliably (reconnect, heartbeats, replay cursors) | **`alpaca-broker-sse-events`** |
| Keeping local state correct: missed-event recovery, polling rails without webhooks, idempotency, status guards | **`alpaca-broker-reconciliation-idempotency`** |
| Backoff, 429 handling, rate-limit headers, concurrency limits, batch sizing | **`alpaca-broker-rate-limits-resilience`** |
| Handling money correctly: decimals vs floats, numbers-as-strings, truncation/rounding | **`alpaca-broker-money-precision`** |

---

## 8. Integration guidance (applies regardless of language)

1. **One base-URL switch, environment-driven.** Never hardcode prod URLs in a code branch.
2. **Hold auth behind one accessor.** Cache the Bearer token with its expiry and refresh it there, so no call site ever handles credentials.
3. **Treat every write as async.** Model the state machine; act on terminal states, not on the `2xx`.
4. **Persist Alpaca's IDs.** Store `account_id`, `order_id`, `journal_id`, `transfer_id` on your local records — they are your only correlation key for events and reconciliation.
5. **Decimals, not floats**, for anything monetary. Parse the string fields into a decimal type.
6. **Reconcile, don't trust the stream.** SSE can drop events; design a polling/heal pass that re-syncs from Alpaca as source of truth (`alpaca-broker-reconciliation-idempotency`).
7. **Respect rate limits proactively.** Watch `X-RateLimit-Remaining`, back off before you get throttled.
8. **Use `client_order_id`** and Alpaca-ID-keyed upserts so retries and duplicate events are safe.

### Language notes (transport only — Alpaca is HTTP/SSE/WS, so any stack works)

- **Python:** `httpx`/`requests` (REST), `httpx`/`aiohttp` or an SSE client for events, `websockets` for data, `decimal.Decimal` for money.
- **TypeScript/Node:** `fetch` (REST), an `EventSource` implementation for SSE (pass the `Authorization` header), `ws` for WebSocket, decimal-as-string or `decimal.js`.
- **Go:** `net/http` (REST + SSE via a streaming `bufio.Scanner`), `gorilla/websocket` for data; be deliberate about money types (`shopspring/decimal` if precision matters).
- **Any language:** SSE is just a long-lived HTTP GET that yields `text/event-stream`; if no SSE client exists, read the response body line-by-line and parse `data:` frames.

Alpaca also publishes official SDKs (`alpaca-py`, `@alpacahq/alpaca-trade-api` / `typescript-sdk`, Go community SDKs). Offer them when the user wants speed, but these skills teach the **wire protocol** so the knowledge transfers to any language or a custom client.
