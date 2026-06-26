# Broker API Skills

Broker API agent skills for building on Alpaca: account onboarding, funding, journals, trading on behalf of accounts, market data, SSE events, reconciliation, rate limits, and money precision.

Start with [`alpaca-broker-integration`](integration/) for base URLs, auth, API-family routing, and cross-cutting conventions. Then load the focused skill for the task.

## Install

List available skills with the Skills CLI:

```bash
npx skills add alpacahq/alpaca-skills --list
```

Install a single broker skill:

```bash
npx skills add alpacahq/alpaca-skills --skill alpaca-broker-integration
```

Install the full repo into Cursor globally:

```bash
npx skills add alpacahq/alpaca-skills --skill '*' -g -a cursor -y
```

For local development from this checkout, use the local path:

```bash
npx skills add . --list
npx skills add . --skill alpaca-broker-integration
```

## Available skills

| Name | Path | Title | Category |
| --- | --- | --- | --- |
| `alpaca-broker-integration` | [integration/](integration/) | Broker API Integration | Foundation |
| `alpaca-broker-account-onboarding` | [account-onboarding/](account-onboarding/) | Account Onboarding & KYC | Broker lifecycle |
| `alpaca-broker-funding-transfers` | [funding-transfers/](funding-transfers/) | Funding & Transfers | Broker lifecycle |
| `alpaca-broker-journals` | [journals/](journals/) | Journals | Broker lifecycle |
| `alpaca-broker-trading-orders` | [trading-orders/](trading-orders/) | Trading on Behalf of Accounts | Broker lifecycle |
| `alpaca-broker-market-data` | [market-data/](market-data/) | Market Data | Broker lifecycle |
| `alpaca-broker-sse-events` | [sse-events/](sse-events/) | Broker SSE Events | Real-time |
| `alpaca-broker-reconciliation-idempotency` | [reconciliation-idempotency/](reconciliation-idempotency/) | Reconciliation & Idempotency | Cross-cutting |
| `alpaca-broker-rate-limits-resilience` | [rate-limits-resilience/](rate-limits-resilience/) | Rate Limits & Resilience | Cross-cutting |
| `alpaca-broker-money-precision` | [money-precision/](money-precision/) | Money & Numeric Precision | Cross-cutting |

For contribution rules, see [CONTRIBUTING.md](../../CONTRIBUTING.md) and [AGENTS.md](../../AGENTS.md).
