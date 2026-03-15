# 币安广场流量预言机 v5.0 - 架构设计文档

## 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    L7: Article Generator (文章生成)           │
│          二阶段写作: crypto-content-writer + humanizer        │
├─────────────────────────────────────────────────────────────┤
│                  data_digest (数据精简层)                      │
│         L0-L5 海量数据 → 核心情报简报 (~500字符)               │
├─────────────────────────────────────────────────────────────┤
│                  L6: Style Analyzer (风格学习)                │
│              个人主页帖子分析 → 写作风格指纹                    │
├─────────────────────────────────────────────────────────────┤
│              L5: Signal Fusion (信号融合引擎)                  │
│    话题融合 | 代币交叉验证 | 情绪融合 | 时机评估 | 策略生成     │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ L0       │ L1       │ L2       │ L3       │ L4              │
│ 广场热帖  │ 社交热度  │ 链上异动  │ 行情分析  │ 新闻+KOL        │
│          │          │          │          │                 │
│ 热门帖子  │ 热度排名  │ 智能钱信号│ BTC/ETH  │ opennews        │
│ 互动率   │ 情绪分析  │ 净流入   │ 技术指标  │ opentwitter     │
│ 热门标签  │ 趋势代币  │ Meme热点 │ 恐惧贪婪  │ @binancezh      │
│ 病毒帖   │ 叙事提取  │ 巨鲸预警 │ 趋势代币  │ 话题分类        │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│                   Skills Hub (官方Skill融合)                  │
│  spot-ticker | social-hype | smart-money | meme-rush | ...  │
├─────────────────────────────────────────────────────────────┤
│                        数据源层                               │
│  币安广场API | Web3 API | Spot API | 6551 API | alternative  │
└─────────────────────────────────────────────────────────────┘
```

## 数据流（v5.0 优化后）

```
L0-L4 并行采集 → L5 信号融合 → data_digest 精简 → L7 二阶段写作
                                    ↑
                              Skills Hub 数据
                              (直接复用，不重复调用)
```

1. L0-L4 五个数据采集层并行运行，各自独立获取数据
2. Skills Hub 获取官方 Skill API 数据（仅调用一次）
3. L5 融合引擎接收全部 5 层报告，执行加权融合
4. L6 风格分析器提取个人写作风格指纹
5. **data_digest 数据精简层**将 L0-L5 + Skills Hub 的海量数据提炼为核心情报简报
6. L7 文章生成引擎接收精简数据，执行二阶段写作流程

## L7 写作流程对比

### v4.x（旧三阶段）

```
Skills Hub → ContentCombo (重复调用!)
                ↓
L0 原始JSON (截断至2000字) + combo_data (截断至3000字)
                ↓
        writing-plans (LLM #1) → 写作计划 JSON
                ↓
        copywriting   (LLM #2) → 文案初稿
                ↓
        humanizer-zh  (LLM #3) → 最终文章
```

### v5.0（新二阶段）

```
L0-L5 + Skills Hub → data_digest → 核心情报 (~500字符)
                                        ↓
                    crypto-content-writer (LLM #1) → 初稿
                                        ↓
                    humanizer 内置规则    (LLM #2) → 最终文章
```

## 评分体系

| 层级 | 评分字段 | 权重 | 说明 |
|------|---------|------|------|
| L0 | square_score | 30% | 广场热度（帖子数、浏览量、互动率） |
| L1 | social_score | 15% | 社交热度（代币讨论量、情绪偏向） |
| L2 | anomaly_score | 20% | 链上异动（智能钱信号、资金流向） |
| L3 | market_score | 20% | 行情状态（技术指标、恐惧贪婪） |
| L4 | news_score | 15% | 新闻热度（新闻量、KOL互动量） |

## data_digest 精简策略

| 数据维度 | 提取规则 | 来源优先级 |
|----------|---------|-----------|
| 情绪摘要 | 融合标签 + 分数 + 建议 | L5 > L3 |
| 热门代币 Top 5 | 符号 + 确信度 + 关键细节 | L5 > L0 |
| 热门话题 Top 3 | 话题名称 | L5 > L0 |
| 行情快照 | 主流币价格 + 24h涨跌 | L3 > Skills Hub |
| 链上信号 | 聪明钱买入/卖出 Top 3 | L2 |
| 内容策略 | 推荐类型 + 推荐代币 | L5 |
| 预言机评分 | 总分 + 评级 | L5 |

## API 端点清单

| 层级 | API | 认证 | 说明 |
|------|-----|------|------|
| L0 | binance.com/bapi/composite/v3/.../article/list | 无需 | 广场热门帖子 |
| L1 | web3.binance.com/.../social/hype/rank/leaderboard | 无需 | 社交热度排名 |
| L1 | web3.binance.com/.../unified/rank/list | 无需 | 趋势代币排名 |
| L2 | web3.binance.com/.../trading-signal/signal/list | 无需 | 智能钱信号 |
| L2 | web3.binance.com/.../smart-money/net-inflow | 无需 | 资金净流入 |
| L2 | web3.binance.com/.../meme-rush/topic/list | 无需 | Meme热点 |
| L3 | data-api.binance.vision/api/v3/klines | 无需 | K线数据 |
| L3 | data-api.binance.vision/api/v3/ticker/24hr | 无需 | 24h行情 |
| L3 | api.alternative.me/fng/ | 无需 | 恐惧贪婪指数 |
| L4 | ai.6551.io/open/news_search | Bearer Token | 新闻搜索 |
| L4 | ai.6551.io/open/twitter_user_tweets | Bearer Token | KOL推文 |

## 降级策略

每层均设计了独立的降级机制：当某层 API 不可用时，系统会返回默认的空报告（评分为 50），不影响其他层的运行和最终融合结果。data_digest 层对缺失数据也有回退逻辑，确保即使部分层失败也能输出有效的核心情报。
