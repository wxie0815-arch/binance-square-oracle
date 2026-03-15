# 发现的关键 API 端点

## 1. 用户 Profile 信息
- URL: `/bapi/composite/v3/friendly/pgc/user/client`
- Method: POST
- Body: `{"username":"CZ","getFollowCount":true,"queryFollowersInfo":true,"queryRelationTokens":true}`
- 返回: squareUid, avatar, displayName, biography, verificationType 等

## 2. 用户帖子列表
- URL: `/bapi/composite/v2/friendly/pgc/content/queryUserProfilePageContentsWithFilter`
- Method: GET
- Params: `targetSquareUid=dxCeCLOM7uOFJKX8EnS3Kw&timeOffset=-1&filterType=ALL`
- 返回: contents 列表，包含帖子详情

## 3. 搜索用户/内容
- URL: `/bapi/composite/v2/friendly/pgc/feed/search/list`
- Method: POST
- Body: `{"scene":"web","pageIndex":1,"pageSize":20,"searchContent":"CZ","type":1}`
- type=1 返回内容搜索结果，包含 KOL_RECOMMEND 和 KOL_SEARCH_GROUP

## 关键发现
- CZ 的 squareUid: `dxCeCLOM7uOFJKX8EnS3Kw`
- 帖子列表使用 squareUid 而非 username
- timeOffset=-1 表示从最新开始
