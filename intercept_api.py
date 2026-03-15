#!/usr/bin/env python3
"""Use Playwright to intercept Binance Square profile page API calls."""
import json
from playwright.sync_api import sync_playwright

captured_requests = []

def handle_request(request):
    url = request.url
    if 'bapi' in url and ('pgc' in url or 'feed' in url or 'profile' in url or 'search' in url):
        captured_requests.append({
            'url': url,
            'method': request.method,
            'post_data': request.post_data,
        })

def handle_response(response):
    url = response.url
    if 'bapi' in url and ('pgc' in url or 'feed' in url or 'profile' in url):
        try:
            body = response.json()
            code = body.get('code')
            data = body.get('data')
            short_url = url.split('binance.com')[1] if 'binance.com' in url else url[:80]
            
            # Find matching request
            post_data = None
            for req in captured_requests:
                if req['url'] == url:
                    post_data = req.get('post_data')
                    break
            
            if data is not None:
                data_preview = json.dumps(data, ensure_ascii=False)[:300]
                print(f'[API] {short_url}')
                print(f'  method: {response.request.method}')
                if post_data:
                    print(f'  body: {post_data[:200]}')
                print(f'  code: {code}')
                print(f'  data: {data_preview}')
                print()
        except:
            pass

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        viewport={'width': 1280, 'height': 720}
    )
    page = context.new_page()
    
    page.on('request', handle_request)
    page.on('response', handle_response)
    
    print('=== Navigating to CZ profile ===')
    page.goto('https://www.binance.com/en/square/profile/cz', wait_until='networkidle', timeout=30000)
    
    print('\n=== Scrolling down to trigger more loads ===')
    for i in range(3):
        page.evaluate('window.scrollBy(0, window.innerHeight)')
        page.wait_for_timeout(2000)
    
    print('\n=== Now try search page ===')
    page.goto('https://www.binance.com/en/square/search?s=CZ', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(3000)
    
    # Click on Creators tab
    try:
        page.click('text=Creators', timeout=5000)
        page.wait_for_timeout(3000)
    except:
        print('Could not click Creators tab')
    
    print(f'\n=== Total captured: {len(captured_requests)} requests ===')
    
    browser.close()
