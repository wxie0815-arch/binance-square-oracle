# Binance Square Oracle

[![Version](https://img.shields.io/badge/version-v1.1-blue)](https://github.com/wxie0815-arch/binance-square-oracle)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-native-green)](https://openclaw.ai)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Skills Hub](https://img.shields.io/badge/Binance-Skills%20Hub-orange)](https://github.com/binance/binance-skills-hub)

Binance Square Oracle is an OpenClaw-native article orchestration skill for the Binance ecosystem.
It keeps the project's original idea intact:

- route by article style
- collect only the data needed for that style
- generate a publish-ready Binance Square article
- output an `oracle_score`
- optionally publish through Binance Square

The project now has two clear operating modes:

1. Recommended: OpenClaw-native mode
2. Optional: local Python prototype mode

## Why This Shape Fits The Competition Better

The competition-facing path should align with the official ecosystem:

- OpenClaw handles model access natively
- official Binance Skills Hub skills provide the data and publishing surface
- this repository provides the orchestration logic, style system, and article packaging

That is much more reliable than hardcoding a private model endpoint inside the skill.

## Preserved Product Features

- 9 built-in article styles
- DIY custom prompt styles in `prompts/`
- style-based data routing
- optional L4 news/KOL enhancement through 6551
- optional L8-style publishing flow through Binance Square
- Binance Square trending monitor sub-skill

## Official Binance Capability Map

The recommended workflow prefers official Binance skills:

- `binance/spot`
- `binance/derivatives-trading-usds-futures`
- `binance/alpha`
- `binance-web3/crypto-market-rank`
- `binance-web3/trading-signal`
- `binance-web3/meme-rush`
- `binance-web3/query-token-info`
- `binance-web3/query-token-audit`
- `binance-web3/query-address-info`
- `binance/square-post`

Reference sources:

- [Binance Skills Hub](https://github.com/binance/binance-skills-hub)
- [Build Your Own Binance Square AI Agent Skill](https://academy.binance.com/ky-KG/articles/build-your-own-binance-square-ai-agent-skill)

## Built-in Styles

| Style | Best For | Core Data Route |
| :--- | :--- | :--- |
| `daily_express` | quick market recap | spot, alpha, market-rank, token-info |
| `deep_analysis` | full thesis write-up | spot, derivatives, alpha, trading-signal, token-info, token-audit |
| `onchain_insight` | wallet and smart-money angle | trading-signal, address-info, token-info, token-audit |
| `meme_hunter` | meme discovery | meme-rush, trading-signal, market-rank, token-info, token-audit |
| `kol_style` | opinionated short analysis | spot, trading-signal, market-rank |
| `oracle` | directional call | spot, derivatives, trading-signal, market-rank |
| `project_research` | token/project intro | token-info, token-audit, alpha, market-rank |
| `trading_signal` | tactical setup | spot, derivatives, trading-signal, token-audit |
| `tutorial` | educational content | spot, market-rank |

DIY styles can be added by dropping a new `.md` file into `prompts/`.

## OpenClaw-Native Usage

Install this repository as a skill in OpenClaw, then ask for outputs such as:

```text
Use deep_analysis style to write a Binance Square article about BTC.
```

```text
Use meme_hunter style to find the hottest meme setup and prepare a publish-ready Square post.
```

```text
Use prompts/my_style.md as my custom style and produce a Square-ready article on ETH.
```

In this mode:

- the root `SKILL.md` is the main product
- OpenClaw supplies the model
- official Binance skills should be preferred for data and publishing

## Local Python Prototype

The Python files remain as a prototype and backup path for local experiments.
They no longer assume a special OpenClaw-only hidden endpoint.

### Local requirements

- Python 3.8+
- `pip install -r requirements.txt`
- an OpenAI-compatible API base URL and API key

### Environment variables

Copy `.env.example` to `.env` and configure what you need:

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- optional `SQUARE_API_KEY`
- optional `TOKEN_6551`
- optional `API_6551_BASE`

Example:

```bash
python3 -c "from oracle import run_oracle; print(run_oracle(style_name='deep_analysis')['final_article'])"
```

## Repository Layout

```text
binance-square-oracle/
├── SKILL.md                         # main OpenClaw-native orchestration skill
├── prompts/                         # built-in and DIY article styles
├── references/writing_rules.md      # local writing baseline rules
├── collect.py                       # local Python data collection prototype
├── oracle.py                        # local Python article generator prototype
├── publish.py                       # local Python Binance Square publishing helper
├── skills/binance-square-monitor/   # optional monitor sub-skill
└── tests/                           # smoke and integration helpers
```

## Validation Notes

Recent cleanup focused on competition readiness:

- removed the hard dependency on a missing submodule for writing rules
- documented an OpenClaw-native execution path
- corrected broken local script assumptions
- kept the original style system and data-route concept

## Attribution

Project author: `wxie0815-arch`

---

## 💰赞助支持

如果这个项目对您有帮助，欢迎赞助支持！

**BSC（BEP-20）钱包地址：** `0x3B74BE938caB987120C3661C8e3161CD838e5a1A`

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者🙏

**作者：** 无邪Infinity | 币安广场@wuxie | X @wuxie149
