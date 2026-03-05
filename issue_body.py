#!/usr/bin/env python3
"""Generate GitHub Issue body from articles-{date}.json"""
import json
from pathlib import Path
from datetime import datetime

date = datetime.now().strftime("%Y-%m-%d")
af = Path(f"articles-{date}.json")

if not af.exists():
    print(f"## ⚠️ 未找到 articles-{date}.json\n\n今日无文章数据。")
    raise SystemExit

articles = json.loads(af.read_text(encoding="utf-8"))
total = len(articles)
top = [a for a in articles if a.get("score", 0) >= 7]

body = f"## 📰 每日文章摘要\n\n**日期**: {date} · 共 {total} 篇，{len(top)} 篇高分 (≥7)\n\n"

for i, a in enumerate(articles, 1):
    score = a.get("score", 0)
    star = "🔥" if score >= 8 else "⭐" if score >= 7 else ""
    body += f"### {i}. {a.get('title_cn', a.get('title_en', ''))}{f' {star}' if star else ''}\n\n"
    body += f"- **评分**: {score}/10\n"
    body += f"- **原标题**: {a.get('title_en', '')}\n"
    body += f"- **来源**: {a.get('source', '')}\n"
    body += f"- **链接**: {a.get('url', '')}\n"
    body += f"- **摘要**: {a.get('summary_cn', '')}\n"
    if a.get("angle"):
        body += f"- **切入角度**: {a['angle']}\n"
    body += "\n"

print(body)
