# Trading on Behalf of Accounts Reference

Companion to `SKILL.md`. Read the workflow and guardrails there first.

## Primary docs and schemas

- Guides: `https://docs.alpaca.markets/docs/orders-at-alpaca`, `https://docs.alpaca.markets/docs/fractional-trading`
- API ref: `https://docs.alpaca.markets/reference/postorder`
- Live schema: `alpaca-docs` MCP → `get-endpoint` title `"Broker API"` path `/v1/trading/accounts/{account_id}/orders`

## Live schema workflow

Prefer live Alpaca documentation before generating code that opens accounts, moves money, places orders, or mutates production state:

1. Check `https://docs.alpaca.markets/llms.txt` or `https://docs.alpaca.markets/llms-full.txt` for the current documentation index.
2. If an `alpaca-docs` MCP server is connected, use it for exact endpoint schemas instead of guessing from examples.
3. Verify required fields, enum values, pagination, and status transitions against the current Broker API, Trading API, or Market Data API spec.

## Related broker skills

`alpaca-broker-integration`, `alpaca-broker-account-onboarding`, `alpaca-broker-funding-transfers`, `alpaca-broker-journals`, `alpaca-broker-market-data`, `alpaca-broker-sse-events`, `alpaca-broker-reconciliation-idempotency`, `alpaca-broker-rate-limits-resilience`, `alpaca-broker-money-precision`
