# 在 Obsidian 维护博客

唯一维护位置：D:\obsidian笔记\obsidian4444\博客。原 D:\4444Hao.github.io 是旧副本，后续不在那里编辑或同步。

## 一次性启用自动发布

1. GitHub 仓库 Settings → Pages → Build and deployment → Source，改成 GitHub Actions。
2. 在 Obsidian Git 检查本次新增与修改的文件，填写提交说明，执行 Commit-and-sync（确认 Push on commit-and-sync 开启）。也可以分别 Commit、Push。不要在此时开启定时自动发布。
3. 在 GitHub Actions 查看 Build and deploy blog，build 和 deploy 都成功后，刷新网站。如果工作流已上传但首次运行失败，切换 Source 后在 Actions 中重新运行，或用 Run workflow 手动触发。

工作流会重新构建 docs，仅上传网页产物。它不会把生成的 docs 和 content/index.json 回写到 GitHub 源码分支，因此仓库中的旧 docs 可能落后于线上网页；线上以 Actions 部署产物为准。

## 日常维护

Obsidian 编辑博客/content 中的笔记 → 保存 → Source Control 检查改动 → Commit-and-sync → GitHub Actions 自动验证、构建、部署 → 刷新网页。

仅有本地 Commit 不会更新网站；需要成功 Push。同步的是整个博客仓库，包括已提交的文件删除。

- 修改：调整正文、标题、摘要、分类或标签后，更新 updated 属性为本次维护日期。
- 新增：在 content 的第一层创建英文文件名，例如 walk-in-wind.md。文件名只用小写字母、数字、连字符；它决定网址，标题可以是中文。
- 删除：删除 content 中的 Markdown，检查 Source Control 的删除项，然后提交并推送。下次成功构建会删除对应网页，重新计算文章、字数、分类分页和标签图谱。Git 历史仍保留曾提交的内容。
- 暂不展示：设置 draft: true；要展示时改为 draft: false。草稿源码在公开仓库中仍可读，私人笔记应放在博客仓库之外。
- 文件名：已有文章不要改文件名或 slug，以免更改网址。如文件已包含 slug，它必须与文件名（不含 .md）一致。
- 分类：仅支持 随笔、短记、摘录、专题整理。tags 是列表，新标签会自动加入图谱，无需修改脚本。
- 内容格式：当前只处理 content/*.md；暂不支持 content 下的子文件夹。Obsidian 双链 [[...]] 和 ![[图片]] 需改成标准 Markdown。

## 使用模板新建文章

1. Obsidian 设置 → 核心插件，启用 Templates（模板）。
2. 模板设置的 Template folder location 选择 博客/templates（若将博客单独打开成库，则选 templates）。
3. 在 博客/content 新建笔记，如 walk-in-wind；按 Ctrl+P，选择 Templates: Insert template，插入 new-post。
4. 将标题、摘要、分类、标签改好。模板插入时自动填写当前日期；以后修改内容时手动更新 updated。
5. draft 默认 true；确定要在网页展示后改为 false，再提交、推送。

也可复制一篇现有文章到 content，改文件名、slug（若有）、标题、摘要、标签和日期。复制模板文件时，需把 updated 中的日期占位符替换成实际 YYYY-MM-DD 日期。

## 图片

图片放入 博客/assets/images，笔记中用标准 Markdown，例如：

![风中的树](/assets/images/tree.webp)

当前图片路径用于网站渲染；Obsidian 本地预览可能无法解析这个站点根路径。第一版先以文字维护为主。

## 构建失败

到仓库 Actions 打开失败运行，查看 Validate blog 或 Build current notes 的错误。常见原因：缺少属性、日期格式不对、分类不在四类内、文件名与 slug 不一致、残留 Obsidian 双链。修正后重新提交并推送。

未通过验证时不会进入部署，线上保留上一次成功发布的版本。

## 可选本地预览

在 VS Code 打开上述博客目录，Ctrl+Shift+B 构建，运行预览任务。首次需 python -m pip install -r requirements.txt。日常自动发布无需本机手动构建。
