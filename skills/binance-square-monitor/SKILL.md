---
name: binance-square-monitor
description: "Monitor Binance Square trending posts and track real-time traffic data including view count, like count, comment count, and share count. Use for scraping Binance Square hot posts, monitoring crypto social media engagement, tracking post traffic changes over time, generating traffic reports."
---

# Binance Square Trending Posts Monitor

Scrape and monitor trending posts from Binance Square, tracking view count, like count, comment count, and share count in real time.

## Quick Start

### Single Fetch (one-time snapshot)

```bash
python3 /home/ubuntu/skills/binance-square-monitor/scripts/binance_square_monitor.py fetch --pages 3 --output ./binance_square_data
```

### Continuous Monitoring

```bash
python3 /home/ubuntu/skills/binance-square-monitor/scripts/binance_square_monitor.py monitor --interval 300 --pages 3 --output ./binance_square_data
```

## Workflow

Monitoring Binance Square trending posts involves these steps:

1. Fetch trending posts via API (`fetch` or `monitor` command)
2. Review terminal output for traffic summary table
3. Check CSV/JSON files for historical data and change tracking
4. Analyze trends using the changes log

## Script Usage

The main script is `scripts/binance_square_monitor.py`. It requires only the `requests` package (pre-installed).

### Commands

**`fetch`** — Single snapshot of trending posts:

| Flag | Default | Description |
|------|---------|-------------|
| `--pages` | 3 | Number of pages to fetch (20 posts/page) |
| `--page-size` | 20 | Posts per page |
| `--output` / `-o` | None | Output directory (omit for terminal-only) |
| `--format` | all | Output format: csv, json, all, print |

**`monitor`** — Continuous monitoring with change tracking:

| Flag | Default | Description |
|------|---------|-------------|
| `--interval` | 300 | Seconds between snapshots |
| `--pages` | 3 | Pages per snapshot |
| `--page-size` | 20 | Posts per page |
| `--output` / `-o` | auto | Output directory |
| `--max-snapshots` | 0 | Max snapshots (0 = unlimited) |

### Output Files

| File | Content |
|------|---------|
| `trending_posts.csv` | All snapshots with full traffic data |
| `trending_posts.json` | Structured JSON with snapshot grouping |
| `changes_log.csv` | Delta values between consecutive snapshots |
| `monitor_report.md` | Summary report (generated on exit) |

## Data Fields Collected

Each post record contains:

| Field | Description |
|-------|-------------|
| post_id | Unique post identifier |
| author | Author display name |
| view_count | Total views |
| like_count | Total likes |
| comment_count | Total comments |
| share_count | Total shares |
| reply_count | Total replies |
| quote_count | Total quotes |
| post_time | Post creation time (UTC) |
| hashtags | Associated hashtags |
| web_link | Direct URL to post |

## Programmatic Usage

Import functions directly for custom workflows:

```python
import sys
sys.path.insert(0, "/home/ubuntu/skills/binance-square-monitor/scripts")
from binance_square_monitor import fetch_trending_posts, fetch_all_trending

# Fetch single page
posts = fetch_trending_posts(page_index=1, page_size=20)

# Fetch multiple pages
all_posts = fetch_all_trending(total_pages=3, page_size=20)

# Each post is a dict with: post_id, author, view_count, like_count,
# comment_count, share_count, reply_count, quote_count, etc.
for p in all_posts:
    print(f"{p['author']}: {p['view_count']} views, {p['like_count']} likes")
```

## API Details

For endpoint documentation, parameters, and response schema, see `references/api_reference.md`.

Key endpoint: `GET /bapi/composite/v3/friendly/pgc/content/article/list?pageIndex=1&pageSize=20&type=1`

No authentication required. Recommended rate limit: 0.5s between pages, 5+ min between monitoring cycles.

## Troubleshooting

**Empty results**: Binance may block requests from certain IPs. Retry after a few minutes or adjust User-Agent header in the script.

**Encoding errors**: The API returns gzip-compressed responses. The `requests` library handles this automatically; `curl` requires `--compressed` flag.
