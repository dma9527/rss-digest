#!/usr/bin/env python3
"""Generate GitHub Issue body from tracking.json"""
import json
from pathlib import Path
from datetime import datetime

date = datetime.now().strftime("%Y-%m-%d")
body = f"## 📋 今日社交内容已生成\n\n**日期**: {date}\n\n"

tf = Path("social/tracking.json")
if tf.exists():
    t = json.loads(tf.read_text())
    for dk in sorted(t.keys(), reverse=True)[:1]:
        gen = t[dk].get("generated", {})
        topics = t[dk].get("topics", [])
        if gen:
            body += "### 已生成话题\n\n"
            for k, v in sorted(gen.items(), key=lambda x: int(x[0])):
                n = int(k) - 1
                topic = topics[n] if n < len(topics) else {}
                body += f"#### Topic {k}: {v['title']}\n\n"
                body += f"- **分数**: {topic.get('score', '?')}\n"
                body += f"- **话题**: {topic.get('topic', '')}\n"
                body += f"- **切入角度**: {topic.get('angle', '')}\n"
                if topic.get('url'):
                    body += f"- **原文**: {topic['url']}\n"
                body += f"- **标签**: {v.get('tags', '')}\n\n"

body += "### 操作\n\n请审核后回复需要发布的话题编号（如：`发布 1 3 5`）\n"
print(body)
