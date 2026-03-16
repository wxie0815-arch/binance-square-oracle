---
name: binance-square-oracle
description: >
  OpenClaw-native Binance Square article orchestrator. It preserves the project's
  multi-style article generation workflow, routes requests through official Binance
  Skills Hub capabilities, produces a publish-ready draft, an oracle score, and can
  optionally publish through Binance Square.
metadata: {"openclaw": {"homepage": "https://github.com/wxie0815-arch/binance-square-oracle"}}
---

# Binance Square Oracle

Use this skill when the user wants to turn Binance ecosystem data into a Binance Square-ready article.
The recommended execution mode is OpenClaw-native:

- Use the host agent's built-in reasoning and model access.
- Use official Binance Skills Hub skills for data gathering and publishing.
- Keep the project's style system, routing logic, oracle score, and publish-ready output format.

Do not hardcode any OpenClaw API endpoint from inside this skill. Inside OpenClaw, the agent already has model access.

## Goal

Produce a high-quality Binance Square article package with:

- `final_article`
- `article_draft`
- `oracle_score` from 0-100
- `style_fingerprint`
- `data_sources_used`
- optional `publish_result`

## Official Binance Skills To Prefer

When available in the user's environment, prefer official Binance Skills Hub skills over ad-hoc scraping:

- `binance/spot`
- `binance/derivatives-trading-usds-futures`
- `binance/alpha`
- `binance-web3/crypto-market-rank`
- `binance-web3/trading-signal`
- `binance-web3/meme-rush`
- `binance-web3/query-token-info`
- `binance-web3/query-token-audit`
- `binance-web3/query-address-info`
- `binance/square-post` when the user explicitly wants to publish

Optional enhancement inputs may still come from:

- `TOKEN_6551` / 6551 hot news and KOL signals
- local monitor outputs from `skills/binance-square-monitor`

## Working Style

Before writing, identify:

- target asset or topic
- preferred style
- whether the user wants publish-ready copy only, or actual publishing
- whether optional L4 or L8 features are enabled

If a requested data source is unavailable, continue with the best official Binance data that is available and say what was missing.

## Style Routing

Use the lightest route that still matches the requested output.

### `daily_express`

Use:

- `binance/spot`
- `binance/alpha`
- `binance-web3/crypto-market-rank`
- `binance-web3/query-token-info`

### `deep_analysis`

Use:

- `binance/spot`
- `binance/derivatives-trading-usds-futures`
- `binance/alpha`
- `binance-web3/trading-signal`
- `binance-web3/query-token-info`
- `binance-web3/query-token-audit`

### `onchain_insight`

Use:

- `binance-web3/trading-signal`
- `binance-web3/query-address-info`
- `binance-web3/query-token-info`
- `binance-web3/query-token-audit`

### `meme_hunter`

Use:

- `binance-web3/meme-rush`
- `binance-web3/trading-signal`
- `binance-web3/crypto-market-rank`
- `binance-web3/query-token-info`
- `binance-web3/query-token-audit`

### `kol_style`

Use:

- `binance/spot`
- `binance-web3/trading-signal`
- `binance-web3/crypto-market-rank`

### `oracle`

Use:

- `binance/spot`
- `binance/derivatives-trading-usds-futures`
- `binance-web3/trading-signal`
- `binance-web3/crypto-market-rank`

### `project_research`

Use:

- `binance-web3/query-token-info`
- `binance-web3/query-token-audit`
- `binance/alpha`
- `binance-web3/crypto-market-rank`

### `trading_signal`

Use:

- `binance/spot`
- `binance/derivatives-trading-usds-futures`
- `binance-web3/trading-signal`
- `binance-web3/query-token-audit`

### `tutorial`

Use:

- `binance/spot`
- `binance-web3/crypto-market-rank`

### DIY custom style

If the user points to a custom prompt file inside `prompts/`, load it and use a balanced default route:

- `binance/spot`
- `binance-web3/crypto-market-rank`
- `binance-web3/trading-signal`
- `binance/alpha`

## Output Workflow

1. Gather only the mapped Binance data.
2. Build a compact structured briefing:
   - price action
   - derivatives or on-chain signals if relevant
   - market sentiment
   - risk flags
   - optional hot news / KOL context
3. Write `article_draft` in the selected style.
4. Score the setup from 0-100 as `oracle_score`.
5. Summarize the tone in one sentence as `style_fingerprint`.
6. Polish into `final_article` so it is ready for Binance Square posting.

## Writing Rules

Use the local rules in `references/writing_rules.md` as the baseline.

Always:

- stay specific about the observed data
- separate facts from inference
- keep the tone sharp and publication-ready
- avoid generic AI filler
- avoid fake certainty or guaranteed-profit language
- avoid inventing unavailable metrics

## Publishing Rules

If the user explicitly asks to publish and the official `binance/square-post` capability is available:

1. Show the publish-ready article first unless the user asked for direct publishing.
2. Keep the post concise enough for Binance Square.
3. Add reasonable hashtags and mentioned coins only if they are actually relevant.
4. Return the publish response as `publish_result`.

If publishing is unavailable, still return the final publish-ready article package.

## Response Format

When the user is asking for generation, prefer returning a compact JSON-like package in prose or code block form containing:

- `style_name`
- `user_intent`
- `data_sources_used`
- `oracle_score`
- `style_fingerprint`
- `article_draft`
- `final_article`
- optional `publish_result`

## Local Prototype

This repository also includes a Python prototype for local testing. That path is optional and should not be treated as the primary OpenClaw integration path.
