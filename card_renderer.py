"""HTML 模板 + Playwright 截图生成小红书卡片"""

COVER_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1080px; height: 1440px; font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  background: linear-gradient(135deg, {bg1} 0%, {bg2} 100%);
  display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px; }}
.badge {{ background: {accent}; color: white; padding: 8px 24px; border-radius: 20px; font-size: 24px; letter-spacing: 2px; margin-bottom: 50px; }}
h1 {{ font-size: 64px; font-weight: 800; color: #1a1a2e; text-align: center; line-height: 1.4; margin-bottom: 20px; }}
.subtitle {{ font-size: 32px; color: #555; text-align: center; line-height: 1.6; margin-bottom: 30px; }}
.sub {{ font-size: 28px; color: {accent}; margin-bottom: 16px; }}
.date {{ font-size: 24px; color: #999; }}
.deco {{ width: 60px; height: 4px; background: {accent}; border-radius: 2px; margin: 30px 0; }}
</style></head><body>
  <div class="badge">每日科技速递</div>
  <div class="deco"></div>
  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
  <div class="deco"></div>
  <div class="date">{date}</div>
</body></html>"""

CARD_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ width: 1080px; min-height: 1080px; font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
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
    ("#7B8FA1", "#f2f4f6", "#7B8FA1"),  # 灰蓝
    ("#9CAF88", "#f4f6f2", "#9CAF88"),  # 灰绿
    ("#C4A882", "#f7f5f2", "#C4A882"),  # 灰棕
    ("#A89BB5", "#f5f3f7", "#A89BB5"),  # 灰紫
    ("#B5838D", "#f7f3f4", "#B5838D"),  # 灰粉
    ("#8BA7A7", "#f2f5f5", "#8BA7A7"),  # 灰青
]

COVER_THEMES = [
    ("#f5f3f0", "#eeebe6"),  # 暖灰
    ("#f0f2f5", "#e8ecf2"),  # 冷灰
    ("#f3f5f0", "#eaf0e6"),  # 灰绿
]


def render_images(xhs_data, out_dir, date_str=""):
    """用 HTML + Playwright 生成小红书封面和卡片图片"""
    from playwright.sync_api import sync_playwright
    import tempfile, random

    title = xhs_data.get("title", "科技速递")
    subtitle = xhs_data.get("subtitle", "")
    cards = xhs_data.get("cards", [])
    if not date_str:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")

    images = []
    theme = random.choice(COVER_THEMES)
    cover_accent = random.choice(ACCENT_COLORS)[0]

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ── 封面 (3:4) ──
        page = browser.new_page(viewport={"width": 1080, "height": 1440})
        html = COVER_HTML.format(
            title=title, subtitle=subtitle, date=date_str,
            bg1=theme[0], bg2=theme[1], accent=cover_accent,
        )
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
            f.write(html)
            f.flush()
            page.goto(f"file://{f.name}")
            cover_path = str(out_dir / "xhs-cover.png")
            page.screenshot(path=cover_path)
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
            )
            with tempfile.NamedTemporaryFile(suffix=".html", mode="w", encoding="utf-8", delete=False) as f:
                f.write(html)
                f.flush()
                page.goto(f"file://{f.name}")
                card_path = str(out_dir / f"xhs-card{i+1}.png")
                page.screenshot(path=card_path, full_page=True)
                images.append(card_path)

        browser.close()

    return images
