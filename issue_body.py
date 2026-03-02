#!/usr/bin/env python3
"""Generate GitHub Issue body from tracking.json"""
import json, sys
from pathlib import Path
from datetime import datetime

date = datetime.now().strftime("%Y-%m-%d")
body = f"## 📋 今日社交内容已生成\n\n**日期**: {date}\n\n"

tf = Path("social/tracking.json")
if tf.exists():
    t = json.loads(tf.read_text())
    for dk in sorted(t.keys(), reverse=True)[:1]:
        gen = t[dk].get("generated", {})
        if gen:
            body += "### 已生成话题\n\n"
            for k, v in sorted(gen.items(), key=lambda x: int(x[0])):
                body += f"- **#{k}** {v['title']}\n"
            body += "\n### 操作\n\n请审核后回复需要发布的话题编号\n"

print(body)
