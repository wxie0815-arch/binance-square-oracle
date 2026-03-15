import requests
import json

BASE_URL = "https://www.binance.com"
ARTICLE_API = f"{BASE_URL}/bapi/composite/v3/friendly/pgc/content/article/list"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

def check_article():
    print("--- Testing Article API (type=2) ---")
    params = {"pageIndex": 1, "pageSize": 5, "type": 2}
    resp = requests.get(ARTICLE_API, params=params, headers=HEADERS)
    data = resp.json()
    vos = data.get("data", {}).get("vos", [])
    if vos:
        first = vos[0]
        print(f"Full First Post Structure: {json.dumps(first, indent=2)}")
        # 检查是否嵌套在 vo 中
        if "vo" in first:
            print("FOUND NESTED 'vo' KEY!")
            print(f"Nested Post ID: {first['vo'].get('id')}")
            print(f"Nested HashtagList: {first['vo'].get('hashtagList')}")
            print(f"Nested Content: {first['vo'].get('content')[:100] if first['vo'].get('content') else 'None'}")
    else:
        print("No vos found")

def check_spot():
    print("\n--- Testing Spot API ---")
    url = "https://api.binance.com/api/v3/ticker/24hr"
    resp = requests.get(url, params={"symbol": "BTCUSDT"})
    print(f"BTCUSDT Return Type: {type(resp.json())}")
    print(f"BTCUSDT Data: {resp.json()}")
    
    resp_all = requests.get(url)
    print(f"All Tickers Return Type: {type(resp_all.json())}")
    print(f"All Tickers Count: {len(resp_all.json()) if isinstance(resp_all.json(), list) else 'N/A'}")

if __name__ == "__main__":
    check_article()
    check_spot()
