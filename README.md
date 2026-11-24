
Obsidian 编辑博客/content 中的笔记 → 保存 → Source Control 检查改动 → Commit-and-sync → GitHub Actions 自动验证、构建、部署 → 刷新网页。

本地构建使用 `python build.py`，生成 `docs/` 并更新 `content/index.json`。默认网址读取 `site.json` 中的 `url`，当前为 `https://4444hao.github.io`。

为 Cloudflare 入口构建时，可通过环境变量 `BLOG_SITE_URL` 指定网址。在 PowerShell 中可这样运行。

```powershell
$env:BLOG_SITE_URL = 'https://4444hao.home64.de'
python build.py
Remove-Item Env:BLOG_SITE_URL
```

该变量仅作用于构建，不改写 `site.json`。网址应为包含 `http://` 或 `https://` 的根地址，可带末尾 `/`，不包含子路径、查询参数或账号密码。页面 canonical、分享网址、RSS 链接、sitemap 和 robots 使用构建网址；RSS 的 GUID 保留 `site.json` 中的网址作为文章标识，以便在两个入口识别同一篇文章。

两个站点分别在独立的 GitHub Actions 工作流中构建。`pages.yml` 使用默认网址发布到 GitHub Pages，`cloudflare-pages.yml` 为 `https://4444hao.home64.de` 构建，并通过 Wrangler 发布到现有项目 `ipv64-test-4444hao`。两个工作流都支持推送 `main` 自动触发和在 Actions 页面手动运行。

Cloudflare 自动部署的首次启用需要以下操作。

1. 在 Cloudflare 创建自定义 API Token，权限选择 `Account / Cloudflare Pages / Edit`，账户资源限定为此 Pages 项目所在的账户。
2. 在 GitHub 仓库的 `Settings → Secrets and variables → Actions → New repository secret` 分别保存 `CLOUDFLARE_API_TOKEN` 和 `CLOUDFLARE_ACCOUNT_ID`。Account ID 可从 Cloudflare 账户控制台地址中找到，通常是 `/` 后的 32 位字符，例如 `dash.cloudflare.com/<Account ID>/workers-and-pages`。
3. 在 Obsidian Git 检查本次代码与文档改动，执行 Commit-and-sync。
4. 在仓库 Actions 页面确认 `Build and deploy blog` 与 `Build and deploy Cloudflare Pages` 两个工作流成功，再检查两个网址和 RSS。

Cloudflare 工作流先只读查询现有项目的 `production_branch`，然后显式向该分支部署。首次真实查询结果会显示在 `Verify existing Cloudflare project and production branch` 步骤中。凭证仅由 Actions Secrets 注入查询和部署步骤。

日常更新仍在 `content/` 中维护笔记，更新 `updated` 后 Commit-and-sync。双站部署成功后，各自的页面、最近笔记、标签图谱与 RSS 一起更新。若某个工作流失败，进入对应运行记录查看失败步骤并重试，网页显示最近一次成功部署的版本。`.preview/` 下的 ZIP 是手动上传时的快照，自动部署每次从仓库源码重新构建。
