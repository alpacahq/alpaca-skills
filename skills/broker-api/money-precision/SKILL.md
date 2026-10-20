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

Orders take **up to 2 decimal places for `notional` and 9 for `qty`** (Broker API FAQ; the order schema's "2 decimal points" on `qty` is stale). Journal `amount` has no documented precision limit — send cash at 2 dp anyway (§3).

**Rule:** explicitly round/truncate to the target precision *before* the API call, using a deliberate rounding mode.

- For **money you're moving out / charging**, **truncate (round down)** to 2 dp so you never move more than intended (e.g. `floor(amount * 100) / 100`). This is house policy, not an API constraint, and it applies to cash only — never truncate a share `qty` this way.
- Pick the rounding mode consciously (`ROUND_DOWN` vs `ROUND_HALF_UP`) — don't inherit whatever the default float formatting does.
- Carry full precision through the arithmetic and round **once**, at the boundary where the value is sent or displayed. Rounding intermediates compounds error.

```
# splitting a deposit across holdings — round each slice down, track remainder
slice = truncate(total * (pct / 100), 2)
```

## 3. Fractional shares

- `notional` takes 2 decimal places, `qty` takes 9. Round each to its own limit before sending.
- `qty` XOR `notional` — never both (see `alpaca-broker-trading-orders`).
- Don't reconstruct `qty` from `notional / price` and send it — pass `notional` and let Alpaca compute the fill. Round-tripping through a price you fetched introduces drift.

## 4. Storage

- Store money in your DB as **fixed-point decimal**, not float, with a scale at least as wide as the widest field you receive — scale ≥ 9 for `qty`, so the 9-dp fractional case can't silently truncate.
- **Store what Alpaca sent verbatim** alongside any converted/derived values. If you truncate to 2 dp for the API call but received more precision back, keep both — it makes reconciliation and audits possible.
- Keep an explicit **currency** column; Alpaca is multi-currency on some rails (funding wallet) even though most is USD.

## 5. Multi-currency notes

- Most Broker/trading flows are USD; journals default to USD.
- The **funding wallet** rail supports many currencies (`USD`, `EUR`, `JPY`, …) and carries FX fees. When you touch it, never assume USD — read and store the `currency`, and treat FX amounts as decimals end-to-end.

## 6. Checklist

- [ ] Money fields parsed from strings into a **decimal** type; serialized back to strings.
- [ ] **No binary floats** anywhere in the move-money path.
- [ ] Amounts rounded/truncated to the allowed precision **before** the call, with an intentional rounding mode (round *down* for outgoing money).
- [ ] Full precision carried through arithmetic; rounded once at the send/display boundary.
- [ ] DB columns are fixed-point decimal with scale ≥ 9; raw Alpaca values stored verbatim.
- [ ] Explicit currency tracked.

**Related skills:** order qty/notional rules → `alpaca-broker-trading-orders`; journal/transfer amounts → `alpaca-broker-journals`, `alpaca-broker-funding-transfers`; reconciling stored vs Alpaca values → `alpaca-broker-reconciliation-idempotency`.
