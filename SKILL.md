---
name: binance-square-oracle
version: 1.1
description: >
  币安广场智能内容预言机。并发采集 11 个币安官方 Skill 数据源（spot、
  derivatives-trading-usds-futures、crypto-market-rank、trading-signal、meme-rush），
  通过 2 次 LLM 调用生成带预言机评分的高质量广场文章，支持 9 种文章风格，
  可选 L4 新闻增强和 L8 广场自动发布。
author: wxie0815-arch
license: MIT
skills_hub: https://github.com/binance/binance-skills-hub

dependencies:
  official_skills:
    - binance/spot@1.0.2
    - binance/derivatives-trading-usds-futures@1.0.0
    - binance-web3/crypto-market-rank@1.0.0
    - binance-web3/trading-signal@1.0.0
    - binance-web3/meme-rush@1.0.0
    - binance/square-post@1.1  # 可选，L8 广场发布
  optional_skills:
    - data_6551  # 可选，L4 新闻 + KOL 信号，需 TOKEN_6551
---

# Binance Square Oracle v1.1

币安广场智能内容预言机，基于币安官方 Skills Hub 的全栈数据驱动内容创作引擎。

---

## Inputs

| 名称 | 类型 | 描述 | 默认值 | 必填 |
| :--- | :--- | :--- | :--- | :--- |
| `symbol` | `string` | CoinGecko 格式代币 ID（如 `bitcoin`、`ethereum`） | `bitcoin` | 否 |
| `futures_symbol` | `string` | 合约交易对（如 `BTCUSDT`、`ETHUSDT`） | `BTCUSDT` | 否 |
| `style_name` | `string` | 文章风格（见下方 9 种风格列表） | `kol_style` | 否 |
| `user_intent` | `string` | 分析主题描述（如"BTC 深度分析"） | `BTC深度分析` | 否 |
| `enable_l4` | `boolean` | 是否启用 L4 新闻 + KOL 增强（需 `TOKEN_6551`） | `false` | 否 |
| `enable_l8` | `boolean` | 是否启用 L8 广场自动发布（需 `SQUARE_API_KEY`） | `false` | 否 |

## Outputs

| 名称 | 类型 | 描述 |
| :--- | :--- | :--- |
| `final_article` | `string` | 经过去 AI 味润色的最终文章 |
| `oracle_score` | `integer` | 预言机市场信心评分（0-100，0 极度看跌，100 极度看涨） |
| `style_fingerprint` | `string` | 文章风格指纹（一句话描述当前风格特征） |
| `article_draft` | `string` | 第一次 LLM 调用生成的初稿（供参考） |

---

## 执行流程（强制指令）

执行此 Skill 时，**必须严格遵循以下步骤，不得跳过任何必选数据源**：

### 步骤 1：并发数据采集（collect.py）

并发调用以下**全部**数据源，将结果合并为一个结构化 JSON 字典：

#### 必选：`binance/spot`（现货行情，无需认证）

```
GET https://api.binance.com/api/v3/ticker/24hr?symbol={FUTURES_SYMBOL}
GET https://api.binance.com/api/v3/klines?symbol={FUTURES_SYMBOL}&interval=1d&limit=7
```

#### 必选：`binance/derivatives-trading-usds-futures`（合约公开数据，无需认证）

```
GET https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={FUTURES_SYMBOL}&period=1h&limit=5
GET https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={FUTURES_SYMBOL}&period=1h&limit=5
GET https://fapi.binance.com/fapi/v1/fundingRate?symbol={FUTURES_SYMBOL}&limit=3
GET https://fapi.binance.com/fapi/v1/openInterest?symbol={FUTURES_SYMBOL}
```

#### 必选：`binance-web3/crypto-market-rank`（社交热度 / Alpha / 智能钱，无需认证）

```
GET  https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/social/hype/rank/leaderboard
     ?chainId=56&sentiment=All&socialLanguage=ALL&targetLanguage=zh&timeRange=1

POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list
     {"rankType":20,"period":50,"sortBy":70,"orderAsc":false,"page":1,"size":10}   # Alpha 发现

POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/unified/rank/list
     {"rankType":10,"period":50,"sortBy":70,"orderAsc":false,"page":1,"size":10}   # 热门趋势

POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/tracker/wallet/token/inflow/rank/query
     {"chainId":"56","period":"1h","tagType":2,"page":1,"pageSize":10}             # 智能钱流入
```

> **请求头要求：** `Content-Type: application/json`，`User-Agent: binance-web3/2.0 (Skill)`

#### 必选：`binance-web3/trading-signal`（链上智能钱信号，无需认证）

```
POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/web/signal/smart-money
     {"smartSignalType":"","page":1,"pageSize":10,"chainId":"CT_501"}
```

#### 必选：`binance-web3/meme-rush`（Meme 叙事追踪，无需认证）

```
POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list
     {"chainId":"CT_501","rankType":10,"limit":10}   # Meme 新发代币

POST https://web3.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/market/token/pulse/rank/list
     {"chainId":"CT_501","rankType":30,"limit":10}   # Meme 迁移代币
```

#### 必选：第三方补充数据（公开接口，无需认证）

```
GET https://api.coingecko.com/api/v3/simple/price?ids={SYMBOL}&vs_currencies=usd&include_24hr_vol=true&include_24hr_change=true&include_7d_change=true
GET https://api.blockchain.info/stats
GET https://api.alternative.me/fng/?limit=7
```

#### 可选：L4 增强层（有 `TOKEN_6551` 时自动启用）

```
POST {API_6551_BASE}/open/news_search
     {"limit":10,"orderBy":"score","timeRange":"6h"}

POST {API_6551_BASE}/open/twitter_user_tweets
     {"username":"binance","limit":2}
```

---

### 步骤 2：分析与写作（oracle.py）

1. 将全部采集数据（JSON 格式）、风格模板（`prompts/{style_name}.md`）和写作规则（`skills/crypto-content-writer/SKILL.md`）注入 `ANALYSIS_WRITING_PROMPT`
2. **第一次 LLM 调用**：输出 `article_draft`（初稿）、`oracle_score`（0-100 评分）、`style_fingerprint`（风格指纹）
3. 将 `article_draft` 注入 `HUMANIZER_PROMPT`
4. **第二次 LLM 调用**：输出 `final_article`（去 AI 味终稿）

---

### 步骤 3：可选发布（publish.py）

- 若 `enable_l8` 为 `true` 且 `SQUARE_API_KEY` 已配置，调用 `binance/square-post` v1.1 接口发布 `final_article`
- 否则跳过，仅返回文章内容

---

## 使用方法

### OpenClaw 调用示例

```
请用"深度分析"风格，生成一篇关于以太坊的市场分析文章。
```

```
启动预言机，分析 BTC 当前市场情绪，使用 KOL 风格，并发布到广场。
```

```
用"Meme 猎手"风格，分析当前最热的 Meme 代币叙事，并给出预言机评分。
```

### 命令行调用示例

```bash
# 最简运行（BTC，KOL 风格）
python3 oracle.py

# 指定代币和风格
python3 -c "
from oracle import run_oracle
result = run_oracle(
    symbol='ethereum',
    futures_symbol='ETHUSDT',
    style_name='deep_analysis',
    user_intent='ETH 以太坊深度分析'
)
print(result['final_article'])
print(f'预言机评分: {result[\"oracle_score\"]}/100')
"

# 启用 L4 新闻增强
TOKEN_6551=your_token python3 -c "
from oracle import run_oracle
r = run_oracle(enable_l4=True)
print(r['final_article'])
"

# 启用 L8 自动发布
SQUARE_API_KEY=your_key python3 -c "
from oracle import run_oracle
from publish import publish_to_square
result = run_oracle(style_name='kol_style')
publish_to_square(result['final_article'])
"
```

---

## 9 种文章风格

| 风格名称 | 文件 | 适用场景 | 特点 |
| :--- | :--- | :--- | :--- |
| `kol_style` | `prompts/kol_style.md` | 日常行情评论 | 个人化、有观点、引发互动 |
| `deep_analysis` | `prompts/deep_analysis.md` | 重大行情解读 | 数据驱动、逻辑严密、专业权威 |
| `daily_express` | `prompts/daily_express.md` | 每日市场速报 | 简洁、快速、信息密度高 |
| `meme_hunter` | `prompts/meme_hunter.md` | Meme 叙事追踪 | 活泼、接地气、捕捉情绪 |
| `onchain_insight` | `prompts/onchain_insight.md` | 链上数据解读 | 技术性强、聪明钱视角 |
| `oracle` | `prompts/oracle.md` | 市场预测 | 神秘感、预测性、高互动 |
| `project_research` | `prompts/project_research.md` | 新项目介绍 | 结构化、客观、适合 Alpha 项目 |
| `trading_signal` | `prompts/trading_signal.md` | 交易建议 | 直接、有操作性、风险提示 |
| `tutorial` | `prompts/tutorial.md` | 科普教育 | 易懂、循序渐进、适合新手 |

---

## 故障排查

**Q: `binance/spot` 和 `binance/derivatives` 数据获取失败？**
A: 这两个接口在部分地区受地理限制。第三方补充数据（CoinGecko、恐惧贪婪指数）会自动作为兜底，确保文章生成不中断。在不受限制的网络环境下，这些接口可以正常访问。

**Q: `web3.binance.com` 接口返回空数据？**
A: 请确保请求头包含 `Content-Type: application/json` 和 `User-Agent: binance-web3/2.0 (Skill)`，POST 请求需要正确的 JSON payload。

**Q: LLM 调用失败？**
A: 确认 OpenClaw 环境已正确配置，或手动设置 `OPENAI_API_KEY` 环境变量。默认使用 `gpt-4.1-mini`，可通过 `OPENCLAW_MODEL` 环境变量覆盖。

**Q: L4 数据跳过？**
A: L4 需要 `TOKEN_6551` 环境变量。未配置时自动跳过，不影响主流程。

**Q: L8 发布跳过？**
A: L8 需要 `SQUARE_API_KEY` 环境变量。未配置时自动跳过，不影响文章生成。

---

## 赞助支持

如果这个 Skill 对您有帮助，欢迎赞助支持！

**BSC（BEP-20）钱包地址：** `0x3B74BE938caB987120C3661C8e3161CD838e5a1A`

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者 🙏

**作者：** [wxie0815-arch](https://github.com/wxie0815-arch) | 币安广场 [@wuxie](https://www.binance.com/en/square/profile/wuxie) | X [@wuxie149](https://x.com/wuxie149)
