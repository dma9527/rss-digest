# RSS Daily Digest

自动抓取 Hacker News 热门博客的 RSS 更新，并生成中文翻译摘要。

## 功能

- 每天自动抓取 100+ 个技术博客的最新文章
- 自动翻译标题为中文
- 生成 Markdown 格式的每日摘要
- 通过 GitHub Actions 自动运行

## 设置步骤

### 1. 创建 GitHub 仓库

```bash
cd /Users/dmawsome/projects/rss-digest
git init
git add .
git commit -m "Initial commit"
gh repo create rss-digest --public --source=. --remote=origin --push
```

### 2. 添加 Anthropic API Key

1. 访问 https://console.anthropic.com/settings/keys
2. 创建新的 API Key
3. 在 GitHub 仓库设置中添加 Secret：
   - 进入仓库 Settings → Secrets and variables → Actions
   - 点击 "New repository secret"
   - Name: `ANTHROPIC_API_KEY`
   - Value: 你的 API Key

### 3. 启用 GitHub Actions

1. 进入仓库的 Actions 标签
2. 启用 workflows
3. 可以手动触发 "Run workflow" 测试

## 本地测试

```bash
cd /Users/dmawsome/projects/rss-digest
pip install -r requirements.txt
export ANTHROPIC_API_KEY='your-api-key'
python fetch_feeds.py
```

## 自定义

### 修改运行时间

编辑 `.github/workflows/daily-digest.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 12 * * *'  # UTC 时间
```

### 修改抓取时间范围

在 `fetch_feeds.py` 中修改 `hours` 参数：

```python
updates = fetch_recent_articles(feeds, hours=48)  # 改为 48 小时
```

## 查看摘要

每天生成的摘要会自动提交到仓库，文件名格式：`digest-YYYY-MM-DD.md`

## 博客来源

使用 [HN Popularity Contest 2025](https://refactoringenglish.com/tools/hn-popularity/) 的结果。
