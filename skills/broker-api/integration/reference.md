# Broker API Integration Reference

Companion to `SKILL.md`. Read the workflow and guardrails there first.

## Primary docs and schemas

- Docs home: `https://docs.alpaca.markets/`
- API reference: `https://docs.alpaca.markets/reference/`
- Machine-readable index: `https://docs.alpaca.markets/llms.txt` and `https://docs.alpaca.markets/llms-full.txt`
- OpenAPI specs: Authentication API, Broker API, Market Data API, Trading API

## Live schema workflow

Prefer live Alpaca documentation before generating code that opens accounts, moves money, places orders, or mutates production state:

1. Check `https://docs.alpaca.markets/llms.txt` or `https://docs.alpaca.markets/llms-full.txt` for the current documentation index.
2. If an `alpaca-docs` MCP server is connected, use it for exact endpoint schemas instead of guessing from examples.
3. Verify required fields, enum values, pagination, and status transitions against the current Broker API, Trading API, or Market Data API spec.

## Related broker skills

`alpaca-broker-account-onboarding`, `alpaca-broker-funding-transfers`, `alpaca-broker-journals`, `alpaca-broker-trading-orders`, `alpaca-broker-market-data`, `alpaca-broker-sse-events`, `alpaca-broker-reconciliation-idempotency`, `alpaca-broker-rate-limits-resilience`, `alpaca-broker-money-precision`
