# Agent Guidelines

Conventions for authoring and maintaining skills in this repository.

## Repository layout

| Path | Purpose |
| --- | --- |
| `skills/trading-api/` | Trading API agent skills |
| `skills/broker-api/` | Broker API agent skills |
| `templates/skill/` | Contributor scaffold (`SKILL.md`) |

## Skill structure

| Topic | Rule |
| --- | --- |
| Layout | Skills live under `skills/<product>/<skill-name>/` |
| Frontmatter | Required fields: `name`, `description` only |
| Skill `name` | `alpaca-<product-scope>-<skill-name>` (e.g. `alpaca-trading-backtest`). `<product-scope>` is `trading` or `broker` — do not include `api` in the name |
| Folder path | Use `skills/trading-api/` or `skills/broker-api/` for product grouping |
| File pairing | Every skill has `SKILL.md` (workflow, guardrails, and detail as needed) |
| Cross-refs | Use relative paths for companion files, not absolute install paths |
| Secrets | Never commit API keys; prefer env vars (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`) |
| Disclosures | Trading skills must include disclosure language in outputs |

## Adding a skill

1. Copy `templates/skill/` into the appropriate product folder.
2. Set `name` to `alpaca-<product-scope>-<skill-name>` (unique within that product folder).
3. Write workflow, guardrails, and any schemas or CLI detail in `SKILL.md`.
4. Open a pull request. A maintainer will review before merge.

## Continuous integration

Pull requests to `main` run `scripts/validate_skills.py` via the `skill-check` GitHub Actions workflow. Fix any reported file and rule before requesting review.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full process.
