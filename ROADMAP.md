# RSS-to-XHS Pipeline Roadmap

## ✅ Completed

- [x] RSS feed auto-fetching via GitHub Actions (daily)
- [x] AI digest generation (Gemini)
- [x] Multi-topic ranking system (`rank` command, AI scores 1-10)
- [x] Per-topic content generation (`gen N` command)
- [x] Tracking system (`social/tracking.json`)
- [x] XHS publishing via MCP tool
- [x] Conversational copywriting style (hook + question ending)
- [x] 6-card carousel per topic
- [x] Scheduled publishing support (`--slot morning/lunch/evening/night`)
- [x] Light-themed PIL card design
- [x] HTML/CSS + Playwright card rendering (Morandi palette)
- [x] Cover with subtitle
- [x] Brand identity: "信号塔Tech" name + avatar
- [x] `batch` command for one-step rank + gen top N
- [x] GitHub Actions: auto fetch → batch gen → create review Issue
- [x] Integrated pipeline: `fetch_feeds.py` outputs `articles.json` with scores
- [x] `rank` reads `articles.json` directly (zero AI calls)
- [x] `gen` uses article's own summary (more precise context)

## 🔜 Next Up

### P0: Card Design Overhaul
- [x] Replace PIL image generation with HTML/CSS + Playwright screenshot
- [x] Morandi color palette
- [x] Design template system (cover + card templates)
- [ ] Consider using Canva API or Figma API as alternative

### P1: Pipeline Integration
- [x] `fetch_feeds.py` outputs `articles.json` with scores during translation
- [x] `rank` reads structured data (no duplicate AI call)
- [x] `gen` uses precise article summary
- [ ] Batch generate top N topics in one command
- [ ] Auto-publish at scheduled China peak hours
- [ ] Track post performance for feedback loop

### P2: Content Quality
- [ ] Feed topic deduplication across days
- [ ] A/B test different title styles
- [ ] Adjust tone/style based on topic category (tech vs food vs privacy)
- [ ] Add source attribution/links in posts

### P3: Account Growth
- [ ] Analyze which topics get most engagement
- [ ] Auto-reply to comments
- [ ] Cross-post to other platforms (Douyin, Weibo)
- [ ] Build consistent visual brand identity
