# Binance Square Oracle

[![Version](https://img.shields.io/badge/version-v1.1-blue)](https://github.com/wxie0815-arch/binance-square-oracle)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-native-green)](https://openclaw.ai)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Skills Hub](https://img.shields.io/badge/Binance-Skills%20Hub-orange)](https://github.com/binance/binance-skills-hub)

**Binance Square Oracle** 是一个面向币安生态的内容生成型 Agent Skill。  
它的目标很明确：

- 按文章风格智能路由数据
- 优先对接币安官方 Skills Hub 能力
- 自动生成可用于币安广场发布的内容
- 给出 `oracle_score` 市场信心评分
- 在可用时直接对接 Binance Square 发布

这个仓库现在分成两种运行方式：

1. **推荐模式：OpenClaw 原生 Skill 模式**
2. **备用模式：本地 Python 原型模式**

---

## 项目定位

如果你要参加币安 Agent 比赛，这个项目的定位不是“单纯抓数据”，而是一个**从币安生态数据到币安广场文章的一键编排器**。

它保留了你原本最有辨识度的产品思路：

- 多风格写作
- 按风格选择最合适的数据源
- 输出发布就绪的广场文案
- 给出结构化评分和风格指纹
- 可选自动发布

---

## 当前功能

### 1. 多风格内容生成

内置 9 种风格：

- `daily_express`
- `deep_analysis`
- `onchain_insight`
- `meme_hunter`
- `kol_style`
- `oracle`
- `project_research`
- `trading_signal`
- `tutorial`

同时支持 DIY 风格。你只需要在 [`prompts/`](/D:/文档/Playground/repo_check/prompts) 下新增一个 `.md` 文件，就可以扩展自己的写作风格。

### 2. 按风格智能路由数据

不同风格不会盲目全量抓取数据，而是按需要调用不同数据能力。

例如：

- `deep_analysis` 更偏向现货、合约、Alpha、链上信号和审计
- `meme_hunter` 更偏向 meme-rush、市场热度、交易信号
- `tutorial` 只走更轻量的基础市场信息

这样更适合比赛展示，因为逻辑清晰，也更像一个真正“有编排能力”的 Agent。

### 3. 对接币安官方 Skills Hub 思路

推荐的 OpenClaw 原生执行路径优先使用这些官方能力：

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

参考：

- [Binance Skills Hub](https://github.com/binance/binance-skills-hub)
- [Build Your Own Binance Square AI Agent Skill](https://academy.binance.com/ky-KG/articles/build-your-own-binance-square-ai-agent-skill)

### 4. 输出发布就绪文章

生成结果的目标不是“草稿笔记”，而是尽量接近可以直接上广场的内容包，核心字段包括：

- `article_draft`
- `final_article`
- `oracle_score`
- `style_fingerprint`
- `publish_result`（启用发布时）

### 5. Oracle 评分机制

项目会基于采集到的数据和风格要求生成一个 `0-100` 的 `oracle_score`，用于表达当前内容中隐含的市场信心强弱。

### 6. 可选增强能力

- **L4 增强**：通过 `TOKEN_6551` 接入热点新闻和 KOL 动态
- **L8 风格发布链路**：通过 `SQUARE_API_KEY` 直接发布到 Binance Square

### 7. Binance Square 热门监控子 Skill

仓库内还保留了 [`skills/binance-square-monitor`](/D:/文档/Playground/repo_check/skills/binance-square-monitor) 这个子 skill，可用于监控币安广场热门帖子、互动数据和流量变化。

---

## 风格与数据映射

| 风格 | 适用场景 | 核心数据能力 |
| :--- | :--- | :--- |
| `daily_express` | 每日市场速递 | spot / alpha / market-rank / token-info |
| `deep_analysis` | 深度分析 | spot / derivatives / alpha / trading-signal / token-info / token-audit |
| `onchain_insight` | 链上洞察 | trading-signal / address-info / token-info / token-audit |
| `meme_hunter` | Meme 追踪 | meme-rush / trading-signal / market-rank / token-info / token-audit |
| `kol_style` | KOL 观点输出 | spot / trading-signal / market-rank |
| `oracle` | 市场预判 | spot / derivatives / trading-signal / market-rank |
| `project_research` | 项目研究 | token-info / token-audit / alpha / market-rank |
| `trading_signal` | 交易观点 | spot / derivatives / trading-signal / token-audit |
| `tutorial` | 教育科普 | spot / market-rank |

---

## 如何使用

### 方式一：OpenClaw 原生 Skill 模式

这是目前**最推荐**的比赛提交和演示方式。

#### 安装

把这个仓库作为 Skill 安装到 OpenClaw 中：

```text
https://github.com/wxie0815-arch/binance-square-oracle
```

#### 使用示例

```text
Use deep_analysis style to write a Binance Square article about BTC.
```

```text
Use meme_hunter style to find the hottest meme setup and prepare a publish-ready Square post.
```

```text
Use prompts/my_style.md as my custom style and produce a Square-ready article on ETH.
```

#### 适合的演示路径

如果你要做比赛 Demo，建议直接展示以下链路：

1. 用户给出一个主题或币种
2. Agent 自动选择风格对应的数据路径
3. 生成 `article_draft`
4. 输出 `oracle_score`
5. 润色成 `final_article`
6. 可选调用发布能力

#### 这个模式的优点

- 更贴近 OpenClaw 官方生态
- 更贴近 Binance Skills Hub 官方叙事
- 更适合评审理解“这是一个 Agent Skill，而不是单纯 Python 脚本”

---

### 方式二：本地 Python 原型模式

这个模式适合你自己本地调试、验证 prompt、测试写作结果。

#### 依赖

- Python 3.8+
- `pip install -r requirements.txt`

#### 环境变量

复制 `.env.example` 为 `.env`，然后按需填写：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `SQUARE_API_KEY`
- `TOKEN_6551`
- `API_6551_BASE`

#### 最小调用示例

```bash
python3 -c "from oracle import run_oracle; r = run_oracle(style_name='deep_analysis'); print(r['final_article'])"
```

#### 启用发布

如果你配置了 `SQUARE_API_KEY`，则本地原型中的 [`publish.py`](/D:/文档/Playground/repo_check/publish.py) 可以把生成结果发到币安广场。

---

## 当前仓库结构

```text
binance-square-oracle/
├── SKILL.md
├── prompts/
├── references/
│   ├── writing_rules.md
│   └── competition_notes.md
├── collect.py
├── oracle.py
├── publish.py
├── skills/
│   └── binance-square-monitor/
└── tests/
```

### 主要文件说明

- [`SKILL.md`](/D:/文档/Playground/repo_check/SKILL.md)：主 Skill 定义，OpenClaw 原生模式的核心入口
- [`collect.py`](/D:/文档/Playground/repo_check/collect.py)：本地原型的数据采集与风格路由
- [`oracle.py`](/D:/文档/Playground/repo_check/oracle.py)：两阶段文章生成逻辑
- [`publish.py`](/D:/文档/Playground/repo_check/publish.py)：发布辅助模块
- [`references/writing_rules.md`](/D:/文档/Playground/repo_check/references/writing_rules.md)：写作规则基线
- [`references/competition_notes.md`](/D:/文档/Playground/repo_check/references/competition_notes.md)：比赛对齐说明

---

## 当前状态

这版仓库已经完成了针对比赛可用性的重构：

- 去掉了缺失 submodule 的硬依赖
- 去掉了对隐藏 OpenClaw 私有端点的依赖假设
- 明确区分了 OpenClaw 原生模式和本地原型模式
- 保留了多风格路由、生成、评分和发布能力
- 补齐了比赛展示所需的文档结构

---

## 项目作者

Project author: `wxie0815-arch`

---

## 💰赞助支持

如果这个项目对您有帮助，欢迎赞助支持！

**BSC（BEP-20）钱包地址：** `0x3B74BE938caB987120C3661C8e3161CD838e5a1A`

支持 USDT / BNB / 任意 BEP-20 代币。感谢每一位支持者🙏

**作者：** 无邪Infinity | 币安广场@wuxie | X @wuxie149
