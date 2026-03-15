# Binance Square API 研究笔记

## 发现的数据源

### 1. 文章列表 API (article/list)
- **端点**: `/bapi/composite/v3/friendly/pgc/content/article/list`
- **type=1 (trending)**: 最多约 9 页 (~180 帖), 覆盖约 24h, 按热度排序
- **type=2 (latest)**: 最多约 50 页 (~1000 帖), 覆盖约 42h, 按时间倒序
- **type=0**: 与 type=2 相同
- **type=3**: 约 20-30 页, 按某种推荐排序
- **type=4/5**: 有数据，待确认
- **pageSize**: 最大 20
- **分页上限**: 约 50 页 (type=2), 9 页 (type=1)

### 2. 新闻 Feed API
- **端点**: `/bapi/composite/v4/friendly/pgc/feed/news/list`
- 最多约 80 页, 覆盖约 52h+
- 与 article/list 的数据有重叠但不完全相同

### 关键结论
- **type=2 (latest)** 是最佳数据源，可覆盖约 42 小时
- **news feed** 可覆盖更长时间 (52h+)
- 两者结合 + 去重，可覆盖 48 小时全量数据
- 所有端点都包含完整的流量指标 (viewCount, likeCount, commentCount, shareCount, replyCount, quoteCount)
- 无需认证，但需要适当的请求间隔

## 升级方案
1. 新增 `fetch-48h` 命令，使用 type=2 + news feed 双数据源
2. 自动分页遍历，按时间截止 (48h前) 停止
3. 帖子去重 (基于 post_id)
4. 输出完整的48小时全量数据
