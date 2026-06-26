---
name: alpaca-broker-money-precision
description: Handle money and numeric precision correctly with the Alpaca API — numbers-as-strings on the wire, decimals vs floats, rounding/truncation before sending amounts, fractional-share precision, and safe DB storage. Use when handling monetary amounts, order quantities, or prices in any Alpaca integration in any language.
---

# Alpaca — Money & Numeric Precision

Financial bugs are silent and expensive. Alpaca's wire format and the realities of decimal arithmetic create a few specific traps. This skill is short, opinionated, and language-agnostic.

> Read `alpaca-broker-integration` first.

## 1. Numbers come as strings — keep them that way

Alpaca returns prices, quantities, notional, and money amounts as **JSON strings** (`"100.50"`, `"1.5"`, `"190.2345"`), and accepts them as strings on the way in. This is deliberate: it avoids the precision loss of JSON's binary floats.

**Rule:** parse string money fields into a **decimal type**, never a binary `float`/`double`. Serialize back to a string. Don't let a number ever live as an IEEE-754 float in the money path.

| Language | Use | Avoid |
|----------|-----|-------|
| Python | `decimal.Decimal("100.50")` | `float("100.50")` |
| TypeScript/JS | a decimal lib (`decimal.js`/`big.js`) or string arithmetic | `Number(...)`, `parseFloat` |
| Go | `shopspring/decimal` | `float64` for accumulation |
| Java/Kotlin | `java.math.BigDecimal` | `double` |

> Real-world caveat: not every Alpaca endpoint is consistent — some market-data numeric fields come as JSON numbers (e.g. bar OHLC). Prices for display/analytics can tolerate floats; **money you move or store must not**. Know which field you're touching.

## 2. Round/truncate before sending — and know the direction

Alpaca generally accepts **2 decimal places for cash** amounts and up to **9 for fractional share `qty`/`notional`**. If you send more precision than allowed, you risk rejection or silent rounding on their side.

**Rule:** explicitly round/truncate to the target precision *before* the API call, using a deliberate rounding mode.

- For **money you're moving out / charging**, **truncate (round down)** to 2 dp so you never move more than intended. (e.g. `floor(amount * 100) / 100`.)
- Pick the rounding mode consciously (`ROUND_DOWN` vs `ROUND_HALF_UP`) — don't inherit whatever the default float formatting does.
- Re-round after every arithmetic step that could reintroduce precision (e.g. computing `amount * percentage` for a split allocation), not just at the end.

```
# splitting a deposit across holdings — round each slice down, track remainder
slice = truncate(total * (pct / 100), 2)
```

## 3. Fractional shares

- `qty` and `notional` support up to **9 decimal places**.
- `qty` XOR `notional` — never both (see `alpaca-broker-trading-orders`).
- Don't reconstruct `qty` from `notional / price` and send it — pass `notional` and let Alpaca compute the fill. Round-tripping through a price you fetched introduces drift.

## 4. Storage

- Store money in your DB as **fixed-point decimal**, not float. A practical pattern is generous precision/scale, e.g. `DECIMAL(20, 8)` — wide enough for multi-currency and fractional, with headroom beyond Alpaca's 2-dp cash so you never lose data you received.
- **Store what Alpaca sent verbatim** alongside any converted/derived values. If you truncate to 2 dp for the API call but received more precision back, keep both — it makes reconciliation and audits possible.
- Keep an explicit **currency** column; Alpaca is multi-currency on some rails (funding wallet) even though most is USD.

## 5. Multi-currency notes

- Most Broker/trading flows are USD; journals default to USD.
- The **funding wallet** rail supports many currencies (`USD`, `EUR`, `JPY`, …) and carries FX fees. When you touch it, never assume USD — read and store the `currency`, and treat FX amounts as decimals end-to-end.

## 6. Checklist

- [ ] Money fields parsed from strings into a **decimal** type; serialized back to strings.
- [ ] **No binary floats** anywhere in the move-money path.
- [ ] Amounts rounded/truncated to the allowed precision **before** the call, with an intentional rounding mode (round *down* for outgoing money).
- [ ] Re-round after each intermediate computation.
- [ ] DB columns are fixed-point decimal with headroom; raw Alpaca values stored verbatim.
- [ ] Explicit currency tracked.

**Related skills:** order qty/notional rules → `alpaca-broker-trading-orders`; journal/transfer amounts → `alpaca-broker-journals`, `alpaca-broker-funding-transfers`; reconciling stored vs Alpaca values → `alpaca-broker-reconciliation-idempotency`.
