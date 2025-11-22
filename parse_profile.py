from pathlib import Path
text = Path('frontend/pages/profile.html').read_text(encoding='utf-8')
start = text.index("document.addEventListener('DOMContentLoaded'")
end = text.index('        // 初始化个人资料页面', start)
print(text[start:end])
