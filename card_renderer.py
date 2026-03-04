"""HTML 模板 + Playwright 截图生成小红书卡片（带中文字体保障 + 图片验证）"""

import os

# ── 字体路径 ──────────────────────────────────────────
FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

def _find_font():
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return f
    return None

def _font_face_css():
    """生成 @font-face CSS，用绝对路径指向本地中文字体"""
    font_path = _find_font()
    if not font_path:
        return ""
    return f"""
    @font-face {{
        font-family: "LocalCJK";
        src: url("file://{font_path}");
        font-weight: 100 900;
    }}
    """

FONT_FAMILY = '"LocalCJK", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif'

# ── 最小文件大小阈值（字节），低于此值视为豆腐图 ──
MIN_CARD_SIZE = 50_000
MIN_COVER_SIZE = 80_000

# ── HTML 模板 ─────────────────────────────────────────

COVER_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{font_face}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1080px; height: {cover_height}px; font-family: {font_family};
  background: linear-gradient(160deg, {bg1} 0%, {bg2} 100%);
  display: flex; flex-direction: column; justify-content: center; padding: 100px 70px; position: relative; }}
.badge {{ background: {accent}; color: white; padding: 10px 28px; border-radius: 24px; font-size: 28px; letter-spacing: 2px; align-self: flex-start; margin-bottom: 44px; }}
h1 {{ font-size: {title_size}px; font-weight: 900; color: #1a1a2e; line-height: 1.2; margin-bottom: 36px; }}
.divider {{ width: 80px; height: 6px; background: {accent}; border-radius: 3px; margin-bottom: 50px; }}
.subtitle {{ font-size: {subtitle_size}px; font-weight: 600; color: #333; line-height: 1.65; margin-bottom: 50px; }}
.points {{ display: flex; flex-direction: column; gap: {points_gap}px; }}
.point {{ display: flex; align-items: flex-start; gap: 20px; }}
.dot {{ width: {dot_size}px; height: {dot_size}px; border-radius: 50%; background: {accent}; margin-top: {dot_mt}px; flex-shrink: 0; }}
.point-text {{ font-size: {point_size}px; color: #444; line-height: 1.5; }}
.date {{ font-size: 26px; color: #aaa; position: absolute; bottom: 60px; left: 70px; }}
</style></head><body>
  <div class="badge">每日科技速递</div>
  <h1>{title}</h1>
  <div class="divider"></div>
  <div class="subtitle">{subtitle}</div>
  <div class="points">{points_html}</div>
  <div class="date">{date}</div>
</body></html>"""

CARD_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
{font_face}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1080px; min-height: 1080px; font-family: {font_family};
  background: {bg}; display: flex; flex-direction: column; padding: 0; }}
.top-bar {{ height: 8px; background: {accent}; }}
.content {{ padding: 70px 80px; display: flex; flex-direction: column; }}
.num {{ font-size: 100px; font-weight: 900; color: {accent}18; line-height: 1; margin-bottom: 0; }}
.card-title {{ font-size: 46px; font-weight: 700; color: {accent}; margin: 10px 0 20px 0; }}
.divider {{ width: 80px; height: 4px; background: {accent}; border-radius: 2px; margin-bottom: 30px; }}
.card-body {{ font-size: 38px; color: #2a2a3a; line-height: 2.0; }}
.footer {{ text-align: center; padding: 40px; color: #bbb; font-size: 22px; border-top: 3px solid {accent}30; margin: 0 80px; }}
</style></head><body>
  <div class="top-bar"></div>
  <div class="content">
    <div class="num">{num}</div>
    <div class="card-title">{card_title}</div>
    <div class="divider"></div>
    <div class="card-body">{card_body}</div>
  </div>
  <div class="footer">{page}</div>
</body></html>"""

ACCENT_COLORS = [
    ("#7B8FA1", "#f2f4f6", "#7B8FA1"),
    ("#9CAF88", "#f4f6f2", "#9CAF88"),
    ("#C4A882", "#f7f5f2", "#C4A882"),
    ("#A89BB5", "#f5f3f7", "#A89BB5"),
    ("#B5838D", "#f7f3f4", "#B5838D"),
    ("#8BA7A7", "#f2f5f5", "#8BA7A7"),
]

COVER_THEMES = [
    ("#f5f3f0", "#eeebe6"),
    ("#f0f2f5", "#e8ecf2"),
    ("#f3f5f0", "#eaf0e6"),
]


def _validate_image(path, min_size):
    """检查图片文件大小，低于阈值说明是豆腐图"""
    size = os.path.getsize(path)
    if size < min_size:
        raise RuntimeError(
            f"豆腐图检测: {path} 只有 {size/1024:.0f}KB (最低 {min_size/1024:.0f}KB)，中文字体可能未加载"
        )


def render_images(xhs_data, out_dir, date_str="", video=False):
    """用 HTML + Playwright 生成小红书封面和卡片图片
    video=True 时生成 9:16 竖屏封面（1080x1920）用于视频
    """
    from playwright.sync_api import sync_playwright
    import tempfile, random

    title = xhs_data.get("title", "科技速递")
    subtitle = xhs_data.get("subtitle", "")
    cards = xhs_data.get("cards", [])
    if not date_str:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")

    font_face = _font_face_css()
    if not font_face:
        raise RuntimeError("未找到中文字体文件，无法渲染")

    images = []
    theme = random.choice(COVER_THEMES)
    cover_accent = random.choice(ACCENT_COLORS)[0]
    cover_height = 1920 if video else 1440
    # 视频封面字体更大，填满 9:16 空间
    subtitle_size = 52 if video else 44
    points_gap = 48 if video else 36
    point_size = 68 if video else 56
    dot_size = 22 if video else 18
    dot_mt = 20 if video else 16

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ── 封面 (3:4 或 9:16) ──
        page = browser.new_page(viewport={"width": 1080, "height": cover_height})
        title_len = len(title)
        title_size = 108 if title_len <= 7 else (88 if title_len <= 10 else (72 if title_len <= 14 else 58))
        points_html = "".join(
            f'<div class="point"><div class="dot"></div><div class="point-text">{c.get("title","")}</div></div>'
            for c in cards[:6]
        )
        html = COVER_HTML.format(
            title=title, subtitle=subtitle, date=date_str,
            bg1=theme[0], bg2=theme[1], accent=cover_accent,
            font_face=font_face, font_family=FONT_FAMILY,
            points_html=points_html, title_size=title_size,
            cover_height=cover_height, points_gap=points_gap,
            subtitle_size=subtitle_size, point_size=point_size,
            dot_size=dot_size, dot_mt=dot_mt,
        )
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
            f.write(html)
            f.flush()
            page.goto(f"file://{f.name}")
            page.wait_for_timeout(500)
            cover_path = str(out_dir / ("xhs-cover-video.png" if video else "xhs-cover.png"))
            page.screenshot(path=cover_path)
            _validate_image(cover_path, MIN_COVER_SIZE)
            images.append(cover_path)
        page.close()

        # ── 卡片 (1:1) ──
        page = browser.new_page(viewport={"width": 1080, "height": 1080})
        for i, card in enumerate(cards):
            accent, bg, _ = ACCENT_COLORS[i % len(ACCENT_COLORS)]
            html = CARD_HTML.format(
                num=f"0{i+1}",
                card_title=card.get("title", ""),
                card_body=card.get("content", ""),
                page=f"{i+1} / {len(cards)}",
                accent=accent, bg=bg,
                font_face=font_face, font_family=FONT_FAMILY,
            )
            with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
                f.write(html)
                f.flush()
                page.goto(f"file://{f.name}")
                page.wait_for_timeout(300)
                card_path = str(out_dir / f"xhs-card{i+1}.png")
                page.screenshot(path=card_path, full_page=True)
                _validate_image(card_path, MIN_CARD_SIZE)
                images.append(card_path)

        browser.close()

    return images
