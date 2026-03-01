#!/usr/bin/env python3
"""从每日 RSS digest 生成小红书图文内容 — 多话题 + 追踪 + 发布流程

用法:
  python generate_social.py rank [--digest FILE]   # AI 给所有文章打分排序
  python generate_social.py list                    # 查看所有话题状态
  python generate_social.py gen N                   # 为第 N 个话题生成小红书内容
  python generate_social.py preview N               # 预览第 N 个话题的生成内容
  python generate_social.py publish N               # 标记为已发布
"""

import argparse
import json
import os
import sys
import glob
import textwrap
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# ── 常量 ──────────────────────────────────────────────

XHS_W, XHS_H = 1080, 1440
TRACKING_FILE = Path("social/tracking.json")

FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

CARD_THEMES = [
    ((245, 245, 250), (235, 240, 250)),
    ((245, 248, 240), (235, 245, 230)),
    ((250, 245, 248), (245, 235, 242)),
    ((245, 248, 255), (230, 240, 255)),
    ((255, 248, 240), (250, 240, 230)),
    ((248, 245, 255), (240, 235, 250)),
]
ACCENT_COLORS = [
    (60, 100, 200), (40, 160, 100), (200, 80, 120),
    (50, 120, 210), (220, 130, 50), (130, 80, 200),
]

# ── Prompts ───────────────────────────────────────────

RANK_PROMPT = """你是一个科技自媒体博主。分析以下 RSS 每日摘要中的所有文章，给每篇文章的"小红书传播力"打分（1-10分）。

评分标准：
- 话题新鲜度和争议性（能引发讨论）
- 与普通人的相关性（不只是开发者关心）
- 标题党潜力（能写出吸引人的标题）
- 科普价值（能用简单语言解释复杂概念）

严格按以下 JSON 格式输出，不要加其他内容：
[
  {{"score": 9, "title": "原文标题", "topic": "用一句话概括话题", "angle": "建议的切入角度"}},
  ...
]

按分数从高到低排序。只输出 JSON 数组。

RSS 摘要：
{digest}
"""

GEN_PROMPT = """你是一个科技自媒体博主，风格参考小红书上的"硅星人"和"Nifty"。

针对以下话题生成一条小红书图文笔记：
话题：{topic}
切入角度：{angle}
原文摘要：{summary}

要求：
- 标题：爆款公式，15字以内，不要用emoji
- 副标题：对标题的补充说明，15-25字，让读者更想点进来
- 正文 400-600 字，口语化聊天风格：
  * 第一句是 hook
  * 用"你"直接对话
  * 短段落，每段2-3句
  * 有观点有态度
  * 最后抛问题引评论
- 6张知识卡片，每张有小标题(8字内)和正文(100-150字，要有具体细节、数据和例子，写得丰富饱满)
- 5-8个 hashtag

严格按以下格式输出：

标题: [标题]
副标题: [副标题，15-25字]
正文:
[正文内容]
标签: [#tag1 #tag2 ...]
卡片1标题: [小标题]
卡片1内容: [正文100-150字，丰富饱满]
卡片2标题: [小标题]
卡片2内容: [正文100-150字]
卡片3标题: [小标题]
卡片3内容: [正文100-150字]
卡片4标题: [小标题]
卡片4内容: [正文100-150字]
卡片5标题: [小标题]
卡片5内容: [正文100-150字]
卡片6标题: [小标题]
卡片6内容: [正文100-150字]
"""

# ── 工具函数 ──────────────────────────────────────────


def find_font():
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return f
    return None


def load_tracking():
    if TRACKING_FILE.exists():
        return json.loads(TRACKING_FILE.read_text(encoding="utf-8"))
    return {}


def save_tracking(data):
    TRACKING_FILE.parent.mkdir(exist_ok=True)
    TRACKING_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_date_key(digest_file):
    return Path(digest_file).stem.replace("digest-", "")


def find_digest(path=None):
    if path and os.path.exists(path):
        return path
    today = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(f"digest-{today}.md"):
        return f"digest-{today}.md"
    files = sorted(glob.glob("digest-*.md"))
    if not files:
        print("未找到任何 digest 文件")
        sys.exit(1)
    return files[-1]


def call_gemini(prompt):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return resp.text.strip()


# ── 解析 ──────────────────────────────────────────────


def parse_xhs_content(text):
    result = {"cards": []}
    current_card_title = None

    for line in text.strip().split("\n"):
        if line.startswith("标题:") or line.startswith("标题："):
            result["title"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
        elif line.startswith("副标题:") or line.startswith("副标题："):
            result["subtitle"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
        elif line.startswith("标签:") or line.startswith("标签："):
            result["tags"] = line.split(":", 1)[-1].split("：", 1)[-1].strip()
        elif "标题" in line and line.startswith("卡片"):
            current_card_title = line.split(":", 1)[-1].split("：", 1)[-1].strip()
        elif "内容" in line and line.startswith("卡片"):
            content = line.split(":", 1)[-1].split("：", 1)[-1].strip()
            result["cards"].append({"title": current_card_title or "", "content": content})
            current_card_title = None

    if "正文:" in text or "正文：" in text:
        body_start = max(text.find("正文:"), text.find("正文："))
        body = text[body_start:].split("\n", 1)[-1]
        for stop in ("标签:", "标签：", "卡片1标题:", "卡片1标题："):
            if stop in body:
                body = body.split(stop)[0]
        result["body"] = body.strip()

    return result


# ── 图片生成 ──────────────────────────────────────────


def _gradient_bg(draw, w, h, c1, c2):
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _generate_ai_cover(title, topic, out_path):
    """AI 生成插画背景 + PIL 叠加清晰文字"""
    font_path = find_font()
    if not font_path:
        return False
    try:
        from google.genai import types
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        prompt = (
            f"Generate a cute cartoon illustration related to: {topic}. "
            "Style: clean white background, kawaii characters, vibrant colors, "
            "NO TEXT at all, no words, no letters, no numbers, pure illustration only. "
            "3:4 aspect ratio, leave upper 40% mostly white/empty for text overlay."
        )
        resp = client.models.generate_content(
            model="gemini-2.0-flash-exp-image-generation",
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        img_data = None
        for part in resp.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                img_data = part.inline_data.data
                break
        if not img_data:
            return False

        # 加载 AI 图片并调整到目标尺寸
        from io import BytesIO
        bg = Image.open(BytesIO(img_data)).convert("RGB").resize((XHS_W, XHS_H), Image.LANCZOS)
        draw = ImageDraw.Draw(bg)

        # 在上部叠加半透明白色区域
        overlay = Image.new("RGBA", (XHS_W, int(XHS_H * 0.45)), (255, 255, 255, 210))
        bg.paste(Image.alpha_composite(
            Image.new("RGBA", overlay.size, (0, 0, 0, 0)), overlay
        ).convert("RGB"), (0, 0))

        # PIL 渲染清晰标题
        ft = ImageFont.truetype(font_path, 58)
        fs = ImageFont.truetype(font_path, 28)
        lines = textwrap.wrap(title, width=14)
        ty = 80
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=ft)
            draw.text(((XHS_W - bbox[2] + bbox[0]) // 2, ty), line, fill=(30, 30, 50), font=ft)
            ty += 80
        ty += 20
        sub = "每日科技速递"
        draw.text(((XHS_W - draw.textbbox((0, 0), sub, font=fs)[2]) // 2, ty), sub, fill=(80, 100, 180), font=fs)

        bg.save(out_path)
        print(f"AI 封面已生成: {out_path}")
        return True
    except Exception as e:
        print(f"AI 生图失败 ({e})，使用 PIL 封面")
    return False


def generate_images(xhs_data, out_dir, topic_text=""):
    font_path = find_font()
    if not font_path:
        print("Warning: 未找到中文字体")
        return []

    title = xhs_data.get("title", "科技速递")
    cards = xhs_data.get("cards", [])
    images = []

    # ── 封面：优先 AI 生图，失败则用 PIL ──
    cover_path = out_dir / "xhs-cover.png"
    if not _generate_ai_cover(title, topic_text or title, cover_path):
        cover = Image.new("RGB", (XHS_W, XHS_H))
        draw = ImageDraw.Draw(cover)
        _gradient_bg(draw, XHS_W, XHS_H, (250, 250, 255), (240, 242, 250))
        ft = ImageFont.truetype(font_path, 60)
        fs = ImageFont.truetype(font_path, 30)
        lines = textwrap.wrap(title, width=13)
        main_color = (60, 100, 200)
        area_top, area_bot = XHS_H // 5, XHS_H * 4 // 5
        draw.rectangle([(80, area_top), (XHS_W - 80, area_top + 4)], fill=main_color)
        lh = 84
        content_h = len(lines) * lh + 60 + 56 + 36
        ty = area_top + 4 + (area_bot - area_top - 4 - content_h) // 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=ft)
            draw.text(((XHS_W - bbox[2] + bbox[0]) // 2, ty), line, fill=(30, 30, 50), font=ft)
            ty += lh
        ty += 60
        sub = "每日科技速递"
        draw.text(((XHS_W - draw.textbbox((0, 0), sub, font=fs)[2]) // 2, ty), sub, fill=main_color, font=fs)
        ty += 56
        date_str = datetime.now().strftime("%Y-%m-%d")
        draw.text(((XHS_W - draw.textbbox((0, 0), date_str, font=fs)[2]) // 2, ty), date_str, fill=(160, 160, 180), font=fs)
        draw.rectangle([(80, area_bot), (XHS_W - 80, area_bot + 4)], fill=main_color)
        cover.save(cover_path)
    images.append(cover_path)

    # ── 卡片（白底彩色） ──
    fn = ImageFont.truetype(font_path, 120)
    fct = ImageFont.truetype(font_path, 46)
    fcb = ImageFont.truetype(font_path, 36)
    fft = ImageFont.truetype(font_path, 24)

    for i, card in enumerate(cards):
        img = Image.new("RGB", (XHS_W, XHS_H))
        draw = ImageDraw.Draw(img)
        theme = CARD_THEMES[i % len(CARD_THEMES)]
        _gradient_bg(draw, XHS_W, XHS_H, theme[0], theme[1])
        accent = ACCENT_COLORS[i % len(ACCENT_COLORS)]

        # 大编号
        draw.text((80, 100), f"0{i+1}", fill=(*accent, 40), font=fn)
        draw.rectangle([(80, 280), (XHS_W - 80, 284)], fill=accent)

        ct = card.get("title", "")
        body_y = 320
        if ct:
            draw.text((80, 320), ct, fill=accent, font=fct)
            body_y = 400

        cc = card.get("content", "")
        cpl = max(1, int((XHS_W - 160) / 36))
        body_lines = []
        for para in cc.split("\n"):
            body_lines.extend(textwrap.wrap(para, width=cpl) or [""])
        body_h = len(body_lines) * int(36 * 1.8)
        text_y = body_y + max(0, ((XHS_H - 200) - body_y - body_h) // 2)
        for line in body_lines:
            draw.text((80, text_y), line, fill=(40, 40, 55), font=fcb)
            text_y += int(36 * 1.8)

        draw.rectangle([(80, XHS_H - 140), (XHS_W - 80, XHS_H - 136)], fill=accent)
        footer = f"{i+1}/{len(cards)}"
        bbox = draw.textbbox((0, 0), footer, font=fft)
        draw.text(((XHS_W - bbox[2] + bbox[0]) // 2, XHS_H - 110), footer, fill=(160, 160, 180), font=fft)

        p = out_dir / f"xhs-card{i+1}.png"
        img.save(p)
        images.append(p)

    return images


# ── 子命令 ────────────────────────────────────────────


def cmd_rank(args):
    """从 articles.json 加载已打分的文章（无需 AI 调用）"""
    digest_file = find_digest(args.digest)
    date_key = get_date_key(digest_file)

    # 优先读 articles.json
    articles_file = f"articles-{date_key}.json"
    if os.path.exists(articles_file):
        topics = json.loads(Path(articles_file).read_text(encoding="utf-8"))
        # 转换为 tracking 格式
        topics = [{"score": a["score"], "title": a["title_en"], "topic": a["title_cn"],
                    "angle": a.get("angle", ""), "summary": a.get("summary_cn", ""),
                    "url": a.get("url", ""), "source": a.get("source", "")}
                   for a in topics if a.get("score", 0) > 0]
        print(f"从 {articles_file} 加载 {len(topics)} 篇文章（已打分，无需 AI）")
    else:
        # Fallback: 用 AI 打分（旧逻辑）
        digest_text = Path(digest_file).read_text(encoding="utf-8")
        print(f"未找到 {articles_file}，使用 AI 打分...")
        raw = call_gemini(RANK_PROMPT.format(digest=digest_text[:12000]))
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        topics = json.loads(raw.strip())

    tracking = load_tracking()
    tracking[date_key] = tracking.get(date_key, {})
    tracking[date_key]["digest_file"] = digest_file
    tracking[date_key]["topics"] = topics
    tracking[date_key]["generated"] = tracking[date_key].get("generated", {})
    tracking[date_key]["published"] = tracking[date_key].get("published", {})
    save_tracking(tracking)

    print(f"\n{'#':<4} {'分数':<6} {'话题'}")
    print("-" * 70)
    for i, t in enumerate(topics):
        status = ""
        gen = tracking[date_key]["generated"]
        pub = tracking[date_key]["published"]
        if str(i + 1) in pub:
            status = " ✅ 已发布"
        elif str(i + 1) in gen:
            status = " 📝 已生成"
        print(f"{i+1:<4} {t['score']:<6} {t['topic']}{status}")
        if t.get("angle"):
            print(f"{'':4} {'':6} 💡 {t['angle']}")

    print(f"\n共 {len(topics)} 个话题。用 `gen N` 生成第 N 个话题的小红书内容。")


def cmd_gen(args):
    """为指定话题生成小红书内容"""
    tracking = load_tracking()
    # 找最新日期
    date_key = sorted(tracking.keys())[-1] if tracking else None
    if not date_key or "topics" not in tracking[date_key]:
        print("请先运行 rank 命令")
        return

    n = args.n
    topics = tracking[date_key]["topics"]
    if n < 1 or n > len(topics):
        print(f"话题编号 {n} 不存在，范围 1-{len(topics)}")
        return

    topic = topics[n - 1]
    digest_file = tracking[date_key]["digest_file"]
    digest_text = Path(digest_file).read_text(encoding="utf-8")

    # 用文章自带的摘要（来自 articles.json），比从 digest 里截取更精确
    summary = topic.get("summary", digest_text[:3000])

    print(f"正在为话题 #{n} 生成小红书内容: {topic['topic']}...")
    raw = call_gemini(GEN_PROMPT.format(
        topic=topic["topic"],
        angle=topic.get("angle", ""),
        summary=summary,
    ))
    content = parse_xhs_content(raw)

    # 保存
    out_dir = Path(f"social/{date_key}/topic-{n}")
    out_dir.mkdir(parents=True, exist_ok=True)

    md_file = out_dir / "xiaohongshu.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(f"# {content.get('title', '')}\n\n")
        f.write(f"{content.get('body', '')}\n\n")
        f.write(f"{content.get('tags', '')}\n")

    # Try HTML renderer first, fall back to PIL
    try:
        from card_renderer import render_images
        images = render_images(content, out_dir, date_str=date_key)
        print(f"HTML 卡片已生成: {len(images)} 张")
    except Exception as e:
        print(f"HTML 渲染失败 ({e})，使用 PIL")
        images = generate_images(content, out_dir, topic_text=topic["topic"])

    # 更新 tracking
    tracking[date_key]["generated"][str(n)] = {
        "title": content.get("title", ""),
        "tags": content.get("tags", ""),
        "dir": str(out_dir),
        "images": [str(p) for p in images],
    }
    save_tracking(tracking)

    print(f"\n✅ 已生成: {out_dir}/")
    print(f"   封面 + {len(content.get('cards', []))} 张卡片")
    print(f"   标题: {content.get('title', '')}")
    print(f"\n用 `preview {n}` 查看内容，`publish {n}` 发布到小红书。")


def cmd_list(args):
    """显示所有话题状态"""
    tracking = load_tracking()
    if not tracking:
        print("暂无数据，请先运行 rank 命令")
        return

    for date_key in sorted(tracking.keys(), reverse=True):
        day = tracking[date_key]
        topics = day.get("topics", [])
        gen = day.get("generated", {})
        pub = day.get("published", {})

        print(f"\n📅 {date_key} ({len(topics)} 个话题)")
        print(f"{'#':<4} {'分数':<6} {'状态':<10} {'话题'}")
        print("-" * 70)
        for i, t in enumerate(topics):
            k = str(i + 1)
            if k in pub:
                status = "✅ 已发布"
            elif k in gen:
                status = "📝 待发布"
            else:
                status = "⬚  未生成"
            print(f"{i+1:<4} {t['score']:<6} {status:<10} {t['topic']}")


def cmd_preview(args):
    """预览已生成的内容"""
    tracking = load_tracking()
    date_key = sorted(tracking.keys())[-1] if tracking else None
    if not date_key:
        print("暂无数据")
        return

    n = str(args.n)
    gen = tracking[date_key].get("generated", {})
    if n not in gen:
        print(f"话题 #{n} 尚未生成，请先运行 gen {n}")
        return

    info = gen[n]
    md_file = Path(info["dir"]) / "xiaohongshu.md"
    print(f"\n{'='*60}")
    print(f"话题 #{n}: {info['title']}")
    print(f"{'='*60}")
    print(md_file.read_text(encoding="utf-8"))
    print(f"\n图片: {len(info.get('images', []))} 张")
    for img in info.get("images", []):
        print(f"  📷 {img}")
    print(f"\n用 `publish {n}` 发布到小红书。")



def cmd_batch(args):
    """自动 rank + gen top N 个话题"""
    # Step 1: rank
    cmd_rank(args)

    tracking = load_tracking()
    date_key = sorted(tracking.keys())[-1]
    topics = tracking[date_key].get("topics", [])
    n = min(args.top, len(topics))

    # Step 2: gen top N
    for i in range(1, n + 1):
        if str(i) in tracking[date_key].get("generated", {}):
            print(f"\n话题 #{i} 已生成，跳过")
            continue
        gen_args = argparse.Namespace(n=i)
        cmd_gen(gen_args)

    # Step 3: 输出摘要
    tracking = load_tracking()  # reload
    gen = tracking[date_key].get("generated", {})
    print(f"\n{'='*60}")
    print(f"📋 批量生成完成: {len(gen)}/{n} 个话题")
    print(f"{'='*60}")
    for k, v in sorted(gen.items(), key=lambda x: int(x[0])):
        print(f"  #{k} {v['title']}")
    print(f"\n用 `preview N` 查看，审核后告诉我发布。")

def cmd_publish(args):
    """标记为已发布 + 输出定时发布信息"""
    tracking = load_tracking()
    date_key = sorted(tracking.keys())[-1] if tracking else None
    if not date_key:
        print("暂无数据")
        return

    n = str(args.n)
    gen = tracking[date_key].get("generated", {})
    if n not in gen:
        print(f"话题 #{n} 尚未生成")
        return

    info = gen[n]
    md_file = Path(info["dir"]) / "xiaohongshu.md"
    lines = md_file.read_text(encoding="utf-8").strip().split("\n")
    if lines[0].startswith("# "):
        lines = lines[1:]
    body = "\n".join(lines).strip()

    # 定时发布时间计算（EST → 北京时间）
    slot = getattr(args, "slot", None)
    schedule_str = None
    if slot:
        from datetime import timedelta
        import pytz
        beijing = pytz.timezone("Asia/Shanghai")
        now_bj = datetime.now(beijing)
        slots = {
            "morning": 8, "lunch": 12, "evening": 20, "night": 21,
        }
        hour = slots.get(slot, 20)
        target = now_bj.replace(hour=hour, minute=30 if slot == "night" else 0, second=0, microsecond=0)
        if target <= now_bj:
            target += timedelta(days=1)
        schedule_str = target.isoformat()
        print(f"⏰ 定时发布: {target.strftime('%Y-%m-%d %H:%M')} 北京时间 ({slot})")

    print(f"\n标题: {info['title']}")
    print(f"图片: {len(info.get('images', []))} 张")
    if schedule_str:
        print(f"定时: {schedule_str}")

    # 输出供 MCP 工具使用的信息
    print(f"\n{'='*40} 发布数据 {'='*40}")
    print(f"TITLE: {info['title']}")
    print(f"TAGS: {info.get('tags', '')}")
    print(f"SCHEDULE: {schedule_str or 'immediate'}")
    print(f"IMAGES:")
    for img in info.get("images", []):
        print(f"  {os.path.abspath(img)}")
    print(f"BODY:\n{body[:200]}...")

    tracking[date_key].setdefault("published", {})[n] = True
    save_tracking(tracking)
    print(f"\n✅ 已标记为发布状态。")


# ── 主入口 ────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="小红书内容生成工具")
    sub = parser.add_subparsers(dest="command")

    p_rank = sub.add_parser("rank", help="AI 给文章打分排序")
    p_rank.add_argument("--digest", help="指定 digest 文件")

    p_batch = sub.add_parser("batch", help="自动 rank + gen top N 个话题")
    p_batch.add_argument("--digest", help="指定 digest 文件")
    p_batch.add_argument("--top", type=int, default=5, help="生成前 N 个话题 (默认 5)")

    p_gen = sub.add_parser("gen", help="生成第 N 个话题的内容")
    p_gen.add_argument("n", type=int, help="话题编号")

    p_list = sub.add_parser("list", help="查看所有话题状态")

    p_preview = sub.add_parser("preview", help="预览第 N 个话题")
    p_preview.add_argument("n", type=int, help="话题编号")

    p_pub = sub.add_parser("publish", help="发布第 N 个话题")
    p_pub.add_argument("n", type=int, help="话题编号")
    p_pub.add_argument("--slot", choices=["morning", "lunch", "evening", "night"],
                       help="定时发布时段 (北京时间: morning=8AM, lunch=12PM, evening=8PM, night=9:30PM)")

    args = parser.parse_args()

    commands = {
        "rank": cmd_rank,
        "batch": cmd_batch,
        "gen": cmd_gen,
        "list": cmd_list,
        "preview": cmd_preview,
        "publish": cmd_publish,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
