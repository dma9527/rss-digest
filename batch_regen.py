#!/usr/bin/env python3
"""批量重新生成所有帖子（基于原文）"""
import json, os, re
from pathlib import Path
from generate_social import call_gemini, parse_xhs_content, fetch_article, GEN_PROMPT
from card_renderer import render_images

POSTS = [
    {"id": "02-26-2", "topic": "三星Galaxy S26 Ultra搭载'隐私显示'功能，有效防止旁人从侧面偷窥屏幕内容。",
     "angle": "三星S26 Ultra逆天功能！别人再也偷看不了你的屏幕了！",
     "url": "https://9to5google.com/2026/02/25/samsung-galaxy-s26-ultra-privacy-display-demo-hands-on/",
     "date": "2026-02-26"},
    {"id": "02-26-3", "topic": "揭露了主要糖果品牌为降低成本，将产品中的真巧克力替换为廉价的'代可可脂巧克力涂层'。",
     "angle": "你吃的巧克力可能是假的！大牌糖果偷偷换了配方，你发现了吗？",
     "url": "https://www.jezebel.com/fake-milk-chocolate-replacements-brands-reeses-hershey-ferrero-compound-coating-candy-climate-change",
     "date": "2026-02-26"},
    {"id": "02-28-1", "topic": "全球最大僵尸网络Kimwolf的操纵者'Dort'的身份揭露及其对披露者的疯狂报复。",
     "angle": "震撼！全球最大僵尸网络黑客身份曝光，疯狂报复揭秘者！",
     "url": "https://krebsonsecurity.com/2026/02/who-is-the-kimwolf-botmaster-dort/",
     "date": "2026-02-28"},
    {"id": "02-28-2", "topic": "西弗吉尼亚州针对苹果CSAM扫描的诉讼，可能因法律缺陷导致儿童性侵者逍遥法外。",
     "angle": "苹果CSAM争议再升级，政府介入反倒可能放过罪犯？",
     "url": "https://www.techdirt.com/2026/02/25/west-virginias-anti-apple-csam-lawsuit-would-help-child-predators-walk-free/",
     "date": "2026-02-28"},
    {"id": "02-28-3", "topic": "通行密钥被错误地用于用户数据加密，导致数据丢失风险。",
     "angle": "紧急警告！你的数据可能因为通行密钥而永远消失！",
     "url": "https://simonwillison.net/2026/Feb/27/passkeys/#atom-everything",
     "date": "2026-02-28"},
    {"id": "02-28-5", "topic": "Block公司裁员近一半员工，导致股价飙升。",
     "angle": "裁员近一半，股价反而暴涨？硅谷这波操作太迷了！",
     "url": "https://www.cnbc.com/2026/02/26/block-laying-off-about-4000-employees-nearly-half-of-its-workforce.html",
     "date": "2026-02-28"},
    {"id": "02-28-7", "topic": "基于树莓派的开源本地化监控系统Frigate升级。",
     "angle": "树莓派DIY最强安防系统！开源、本地化、AI识别！",
     "url": "https://www.jeffgeerling.com/blog/2026/upgrading-my-open-source-pi-surveillance-server-frigate/",
     "date": "2026-02-28"},
    {"id": "02-28-9", "topic": "AI编程智能体在实际应用中的能力和潜力，来自一个怀疑论者的深度实践。",
     "angle": "AI真能取代程序员？一位怀疑论者的深度实践测评！",
     "url": "https://minimaxir.com/2026/02/ai-agent-coding/",
     "date": "2026-02-28"},
    {"id": "03-02-1", "topic": "严厉批评网络上泛滥的低质量AI生成内容，倡导创作者慎用AI或提升内容质量。",
     "angle": "AI烂文泛滥成灾！没人想看你的AI生成内容！",
     "url": "https://pluralistic.net/2026/03/02/nonconsensual-slopping/",
     "date": "2026-03-02"},
    {"id": "03-02-2", "topic": "美国国土安全部数据泄露事件，黑客组织披露攻击动机。",
     "angle": "美国土安全部被攻破！黑客公开宣言震惊全网！",
     "url": "https://micahflee.com/why-hack-the-dhs-i-can-think-of-a-couple-pretti-good-reasons/",
     "date": "2026-03-02"},
    {"id": "03-02-3", "topic": "大模型早期时代由'专家型新手'和'独行侠'主导的趋势分析。",
     "angle": "揭秘普通人如何在AI大潮中抓住机遇！",
     "url": "https://www.jeffgeerling.com/blog/2026/expert-beginners-and-lone-wolves-dominate-llm-era/",
     "date": "2026-03-02"},
]

def gen_one(post):
    print(f"\n{'='*60}")
    print(f"处理: {post['id']} - {post['topic'][:30]}...")
    print(f"{'='*60}")

    article = fetch_article(post["url"])
    if not article:
        print(f"  ⚠️ 原文抓取失败，跳过")
        return None

    raw = call_gemini(GEN_PROMPT.format(
        topic=post["topic"],
        angle=post["angle"],
        summary=post["topic"],
        article=article,
    ))
    content = parse_xhs_content(raw)

    safe_title = re.sub(r'[\\/:*?"<>|！？。，]', '', content.get('title', 'post'))[:30].strip()
    out_dir = Path(f"social/regen/{post['id']}-{safe_title}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 保存 markdown
    with open(out_dir / "xiaohongshu.md", "w", encoding="utf-8") as f:
        f.write(f"# {content.get('title', '')}\n\n")
        f.write(f"{content.get('body', '')}\n\n")
        f.write(f"{content.get('tags', '')}\n")

    # 渲染图片
    images = render_images(content, out_dir, date_str=post["date"])

    # 保存发布数据
    result = {
        "id": post["id"],
        "title": content.get("title", ""),
        "body": content.get("body", ""),
        "tags": content.get("tags", ""),
        "images": [str(p) for p in images],
        "dir": str(out_dir),
    }
    Path(out_dir / "publish_data.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  ✅ {content.get('title', '')} ({len(images)} 张图)")
    return result


if __name__ == "__main__":
    results = []
    for post in POSTS:
        try:
            r = gen_one(post)
            if r:
                results.append(r)
        except Exception as e:
            print(f"  ❌ 失败: {e}")

    print(f"\n{'='*60}")
    print(f"完成: {len(results)}/{len(POSTS)} 篇")
    for r in results:
        print(f"  ✅ {r['id']}: {r['title']}")
