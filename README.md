# 走心旁白 · Obsidian 博客维护工作流

网站：https://4444hao.github.io/

源码：https://github.com/4444Hao/4444Hao.github.io

Obsidian 编辑 content 中的 Markdown
→ 保存
→ Git Source Control 检查本次新增、修改、删除
→ 填写提交说明
→ Commit-and-sync（包含推送），或分别 Commit、Push
→ GitHub Actions 验证、构建、部署
→ 刷新网站确认

RSS 订阅地址：https://4444hao.github.io/feed.xml

公开笔记（`draft: false`）会按已有的 `updated` 时间自动进入最近 20 条 RSS；新建时无需填写 `published`。修订笔记时更新 `updated`，网站和订阅源会一起重新构建；文章链接保持不变，阅读器是否再次提醒旧文章由阅读器决定。草稿不进入 RSS。

