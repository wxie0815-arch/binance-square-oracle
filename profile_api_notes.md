# 币安广场个人主页 API 研究笔记

## 页面 URL 模式
- 个人主页: `https://www.binance.com/en/square/profile/{username}`
- 搜索: `https://www.binance.com/en/square/search?s={keyword}`

## CZ 主页数据
- 用户名: CZ
- 认证: Verified Creator
- 简介: @Binance co-founder and former CEO
- 关注: 27 Following
- 粉丝: 1.7M+ Followers
- 被赞: 275.6K+ Liked
- 被分享: 12.3K+ Shared
- 标签页: All, Quotes, Live

## 帖子数据字段（从页面可见）
- 发布时间
- 内容文本
- 点赞数
- 评论数
- 分享数（转发）
- 浏览量

## 需要探索的 API
1. 搜索用户 API
2. 获取用户 profile API
3. 获取用户帖子列表 API（分页）
