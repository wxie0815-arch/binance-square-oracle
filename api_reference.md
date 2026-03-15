# Binance Square API Reference

## Trending Articles Endpoint

**URL**: `https://www.binance.com/bapi/composite/v3/friendly/pgc/content/article/list`

**Method**: GET

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| pageIndex | int | Yes | Page number, starting from 1 |
| pageSize | int | Yes | Items per page, max 20 |
| type | int | No | 1 = trending articles |

**Required Headers**:

| Header | Value |
|--------|-------|
| User-Agent | Standard browser UA string |
| Accept | application/json |
| Accept-Encoding | gzip, deflate, br |
| Referer | https://www.binance.com/zh-CN/square/trending |

**Response Structure** (key fields per post):

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique post ID |
| authorName | string | Author display name |
| authorIsVerified | boolean | Whether author is verified |
| cardType | string | Post type (BUZZ_SHORT, ARTICLE, etc.) |
| title | string | Post title (may be null for short posts) |
| content | string | Post body text |
| viewCount | int | Total view count |
| likeCount | int | Total like count |
| commentCount | int | Total comment count |
| shareCount | int | Total share count |
| replyCount | int | Total reply count |
| quoteCount | int | Total quote count |
| date | int | Unix timestamp of post creation |
| webLink | string | Web URL to the post |
| hashtagList | array | List of hashtag strings |
| images | array | List of image URLs |
| isFeatured | boolean | Whether post is featured |
| detectedLanguage | string | Detected language code |

## Additional Endpoints

| Endpoint | Description |
|----------|-------------|
| `/bapi/composite/v2/public/pgc/hashtag/hot-list` | Hot hashtags list |
| `/bapi/composite/v4/friendly/pgc/feed/news/list` | News feed |
| `/bapi/composite/v1/friendly/pgc/card/fearGreedHighestSearched` | Fear & Greed index + top searched |

## Rate Limiting

No explicit rate limit documented. Recommended: 0.5s delay between paginated requests, 5+ minute intervals for monitoring.
