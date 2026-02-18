#!/usr/bin/env python3
import feedparser
import os
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

# 支持多个 AI 提供商
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

def parse_opml(opml_file):
    """解析 OPML 文件获取所有 RSS 源"""
    tree = ET.parse(opml_file)
    root = tree.getroot()
    feeds = []
    
    for outline in root.findall('.//outline[@type="rss"]'):
        feeds.append({
            'title': outline.get('text'),
            'url': outline.get('xmlUrl')
        })
    
    return feeds

def is_recent(published_parsed, hours=24):
    """检查文章是否在指定时间内发布"""
    if not published_parsed:
        return False
    
    published = datetime(*published_parsed[:6])
    cutoff = datetime.now() - timedelta(hours=hours)
    return published > cutoff

def fetch_recent_articles(feeds, hours=24):
    """抓取最近的文章"""
    updates = []
    
    for feed_info in feeds:
        try:
            feed = feedparser.parse(feed_info['url'])
            
            recent = []
            for entry in feed.entries[:10]:
                pub_time = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
                if is_recent(pub_time, hours):
                    recent.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': pub_time
                    })
            
            if recent:
                updates.append({
                    'blog': feed_info['title'],
                    'url': feed_info['url'],
                    'articles': recent
                })
        except Exception as e:
            print(f"Error fetching {feed_info['title']}: {e}")
    
    return updates

def translate_titles(client, articles, provider='gemini'):
    """批量翻译标题"""
    if not articles:
        return []
    
    titles = [a['title'] for a in articles]
    prompt = f"""请将以下英文标题翻译成中文，保持简洁准确。每行一个翻译，不要添加序号或其他内容：

{chr(10).join(titles)}"""
    
    if provider == 'gemini':
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        translations = response.text.strip().split('\n')
    else:  # anthropic
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        translations = response.content[0].text.strip().split('\n')
    
    return [t.strip() for t in translations if t.strip()]

def generate_markdown(updates, client, provider='gemini'):
    """生成 Markdown 摘要"""
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'digest-{today}.md'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# RSS 每日摘要 - {today}\n\n")
        f.write(f"共 {len(updates)} 个博客有更新，{sum(len(u['articles']) for u in updates)} 篇新文章\n\n")
        f.write("---\n\n")
        
        for blog in updates:
            f.write(f"## {blog['blog']}\n\n")
            
            translations = translate_titles(client, blog['articles'], provider)
            
            for i, article in enumerate(blog['articles']):
                translation = translations[i] if i < len(translations) else article['title']
                f.write(f"### {translation}\n\n")
                f.write(f"**原标题:** {article['title']}\n\n")
                f.write(f"**链接:** {article['link']}\n\n")
                f.write("---\n\n")
    
    print(f"Generated {filename}")
    return filename

def main():
    # 检测使用哪个 AI 提供商
    provider = os.environ.get('AI_PROVIDER', 'gemini').lower()
    
    if provider == 'gemini':
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("Error: GEMINI_API_KEY not set")
            return
        if not HAS_GEMINI:
            print("Error: google-genai not installed. Run: pip install google-genai")
            return
        client = genai.Client(api_key=api_key)
        print("Using Gemini 2.5 Flash")
    else:  # anthropic
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("Error: ANTHROPIC_API_KEY not set")
            return
        if not HAS_ANTHROPIC:
            print("Error: anthropic not installed. Run: pip install anthropic")
            return
        client = anthropic.Anthropic(api_key=api_key)
        print("Using Claude")
    
    print("Parsing OPML...")
    feeds = parse_opml('hn-blogs-2025.opml')
    print(f"Found {len(feeds)} feeds")
    
    print("Fetching recent articles...")
    updates = fetch_recent_articles(feeds, hours=24)
    print(f"Found {len(updates)} blogs with updates")
    
    if updates:
        print("Generating digest...")
        generate_markdown(updates, client, provider)
    else:
        print("No new articles found")

if __name__ == '__main__':
    main()
