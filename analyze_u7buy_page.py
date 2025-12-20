import requests
import re
import json
from urllib.parse import urljoin

def analyze_page():
    url = "https://www.u7buy.com/fortnite/fortnite-accounts"
    
    # 设置请求头模拟浏览器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"状态码: {response.status_code}")
        
        # 从 HTML 中提取信息
        html_content = response.text
        
        # 查找页面标题
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        if title_match:
            print(f"页面标题: {title_match.group(1)}")
        
        # 查找 JSON 数据
        json_matches = re.findall(r'window\.__NUXT__\s*=\s*({.*?});', html_content, re.DOTALL)
        for i, match in enumerate(json_matches):
            try:
                data = json.loads(match)
                print(f"\n找到 JSON 数据块 {i+1}:")
                if 'config' in data and 'public' in data['config']:
                    public_data = data['config']['public']
                    if 'site' in public_data:
                        print(f"网站环境: {public_data.get('site', {})}")
                    if 'i18n' in public_data:
                        locales = public_data['i18n'].get('locales', [])
                        print(f"支持的语言: {[loc.get('name', loc.get('code', '')) for loc in locales]}")
            except json.JSONDecodeError:
                print(f"JSON 解析失败: {match[:100]}...")
        
        # 查找可能的 API 端点
        api_patterns = [
            r'["\']([^"\']*api[^"\']*)["\']',
            r'["\']([^"\']*fortnite[^"\']*)["\']',
            r'["\']([^"\']*account[^"\']*)["\']'
        ]
        
        found_apis = set()
        for pattern in api_patterns:
            matches = re.findall(pattern, html_content)
            for match in matches:
                if any(keyword in match.lower() for keyword in ['api', 'fortnite', 'account']):
                    found_apis.add(match)
        
        if found_apis:
            print(f"\n找到可能的 API 端点或相关路径:")
            for api in found_apis:
                print(f"  - {api}")
        
        # 分析 URL 路径
        print(f"\nURL 分析:")
        print(f"  域名: u7buy.com")
        print(f"  路径: /fortnite/fortnite-accounts")
        print(f"  推断: 这是一个专门销售 Fortnite 游戏账户的页面")
        
    except requests.RequestException as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    analyze_page()
