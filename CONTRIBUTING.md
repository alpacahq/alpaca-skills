# Contributing

Thank you for contributing to Alpaca Skills. This repository is open to improvements, new skills, and documentation updates.

## Types of contributions

- **New skills** — workflow packages for Trading API or Broker API tasks
- **Improvements** — clearer instructions, better guardrails, broader CLI coverage
- **Documentation** — README and skill docs

## Before you open a PR

1. Read [AGENTS.md](AGENTS.md) for layout and frontmatter conventions.
2. Pick a product folder: `skills/trading-api/` or `skills/broker-api/`.
3. Choose a `name` following `alpaca-<product-scope>-<skill-name>` (e.g. `alpaca-trading-my-skill`). `<product-scope>` is `trading` or `broker`.
4. Copy `templates/skill/` as your starting point.
5. Run `python3 scripts/validate_skills.py` locally before pushing.

For security issues, see [SECURITY.md](SECURITY.md). This project is licensed under the [Apache License 2.0](LICENSE).

## Skill requirements

Every skill must include:

- `SKILL.md` with `name` and `description` frontmatter
- Prerequisites and authentication guidance (no hardcoded secrets)
- Disclosure language for trading-related outputs
- A clear workflow the agent can follow step by step

## Review criteria

Maintainers check for:

- Unique `name` within the product folder
- Disclosure and compliance language where applicable
- Accurate CLI or API references (prefer `alpaca <cmd> --help` and `--schema` over stale examples)
- No committed secrets or credentials

## Pull request process

1. Fork the repository and create a feature branch.
2. Make your changes and self-review against [AGENTS.md](AGENTS.md).
3. Use the [pull request template](.github/PULL_REQUEST_TEMPLATE.md) when opening a PR.
4. Ensure `python3 scripts/validate_skills.py` passes (also enforced by the `skill-check` CI workflow).
5. A maintainer will review and merge or request changes.

Questions? Open a discussion or issue on GitHub.
