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
                    # 获取文章摘要或内容
                    summary = ''
                    if hasattr(entry, 'summary'):
                        summary = entry.summary
                    elif hasattr(entry, 'content'):
                        summary = entry.content[0].value if entry.content else ''
                    
                    recent.append({
                        'title': entry.title,
                        'link': entry.link,
                        'published': pub_time,
                        'summary': summary
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

def translate_and_summarize(client, articles, provider='gemini'):
    """批量翻译标题、生成摘要、打传播力分数"""
    if not articles:
        return []
    
    results = []
    for article in articles:
        prompt = f"""请完成以下任务：
1. 将标题翻译成中文
2. 根据以下内容生成 50-100 字的中文摘要
3. 给这篇文章的"小红书传播力"打分（1-10分），考虑话题新鲜度、与普通人的相关性、标题党潜力、科普价值
4. 如果分数>=7，建议一个小红书切入角度

标题: {article['title']}
内容: {article['summary'][:500] if article['summary'] else '无内容预览'}

请按以下格式输出：
翻译: [中文标题]
摘要: [50-100字的中文摘要]
评分: [1-10的数字]
角度: [切入角度，如果评分<7则写"无"]"""
        
        try:
            if provider == 'gemini':
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                text = response.text.strip()
            else:  # anthropic
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
                text = response.content[0].text.strip()
            
            # 解析响应
            lines = text.split('\n')
            translation = ''
            summary = ''
            score = 5
            angle = ''
            
            for line in lines:
                if line.startswith('翻译:') or line.startswith('翻译：'):
                    translation = line.split(':', 1)[-1].split('：', 1)[-1].strip()
                elif line.startswith('摘要:') or line.startswith('摘要：'):
                    summary = line.split(':', 1)[-1].split('：', 1)[-1].strip()
                elif line.startswith('评分:') or line.startswith('评分：'):
                    try:
                        score = int(line.split(':', 1)[-1].split('：', 1)[-1].strip())
                    except ValueError:
                        score = 5
                elif line.startswith('角度:') or line.startswith('角度：'):
                    angle = line.split(':', 1)[-1].split('：', 1)[-1].strip()
                    if angle == '无':
                        angle = ''
            
            results.append({
                'translation': translation or article['title'],
                'summary': summary or '无摘要',
                'score': score,
                'angle': angle,
            })
        except Exception as e:
            print(f"Error processing article: {e}")
            results.append({
                'translation': article['title'],
                'summary': '处理失败',
                'score': 0,
                'angle': '',
            })
    
    return results

def generate_markdown(updates, client, provider='gemini'):
    """生成 Markdown 摘要 + articles.json"""
    import json
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'digest-{today}.md'
    all_articles = []
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# RSS 每日摘要 - {today}\n\n")
        f.write(f"共 {len(updates)} 个博客有更新，{sum(len(u['articles']) for u in updates)} 篇新文章\n\n")
        f.write("---\n\n")
        
        for blog in updates:
            f.write(f"## {blog['blog']}\n\n")
            
            # 翻译和生成摘要
            results = translate_and_summarize(client, blog['articles'], provider)
            
            for i, article in enumerate(blog['articles']):
                result = results[i] if i < len(results) else {'translation': article['title'], 'summary': '无摘要', 'score': 0, 'angle': ''}
                
                f.write(f"### {result['translation']}\n\n")
                f.write(f"- **来源**: {blog['blog']}\n")
                f.write(f"- **原标题**: {article['title']}\n")
                f.write(f"- **链接**: {article['link']}\n")
                f.write(f"- **摘要**: {result['summary']}\n\n")
                f.write("---\n\n")

                all_articles.append({
                    "title_en": article['title'],
                    "title_cn": result['translation'],
                    "summary_cn": result['summary'],
                    "source": blog['blog'],
                    "url": article['link'],
                    "score": result.get('score', 0),
                    "angle": result.get('angle', ''),
                })
    
    # 输出 articles.json（按分数排序）
    all_articles.sort(key=lambda x: x['score'], reverse=True)
    json_file = f'articles-{today}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, ensure_ascii=False, indent=2)

    print(f"Generated {filename}")
    print(f"Generated {json_file} ({len(all_articles)} articles, top score: {all_articles[0]['score'] if all_articles else 0})")
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
