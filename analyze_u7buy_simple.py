import requests
import re

def analyze_page():
    url = "https://www.u7buy.com/fortnite/fortnite-accounts"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    try:
        response = requests.get(url, headers=headers)
        print("Status Code:", response.status_code)
        
        html_content = response.text
        
        # Look for title
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        if title_match:
            print("Page Title:", title_match.group(1))
        
        # Look for meta description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
        if desc_match:
            print("Description:", desc_match.group(1))
        
        # Look for keywords
        keywords_match = re.search(r'<meta[^>]*name=["\']keywords["\'][^>]*content=["\']([^"\']*)["\']', html_content, re.IGNORECASE)
        if keywords_match:
            print("Keywords:", keywords_match.group(1))
        
        print("\n=== URL Analysis ===")
        print("Domain: u7buy.com")
        print("Path: /fortnite/fortnite-accounts")
        print("Analysis: This page appears to sell Fortnite game accounts")
        
        print("\n=== What U7Buy Sells ===")
        print("Based on the URL structure and domain knowledge:")
        print("- U7Buy is a gaming marketplace")
        print("- This specific page sells Fortnite accounts")
        print("- These are likely pre-existing Fortnite game accounts with:")
        print("  * Rare skins and cosmetics")
        print("  * High account levels")
        print("  * Battle Pass progress")
        print("  * Exclusive items")
        print("  * V-Bucks or in-game currency")
        
    except requests.RequestException as e:
        print("Request failed:", e)

if __name__ == "__main__":
    analyze_page()
