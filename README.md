# 风过枝间 · Obsidian 博客维护工作流

网站：https://4444hao.github.io/

源码：https://github.com/4444Hao/4444Hao.github.io

这个仓库放在 Obsidian 笔记库的「博客」文件夹里。日常在 `博客/content/` 写作，使用 Git 插件提交并推送，GitHub Actions 负责生成网页并发布。本文和模板是维护资料，位于 content 之外，不会作为文章出现在网站中。

## 1. 先确认维护位置和发布方式

- 当前维护目录：`D:\obsidian笔记\obsidian4444\博客`。以后在 VS Code 中也打开这一份，避免与旧目录 `D:\4444Hao.github.io` 分别修改。
- 插件 Advanced → Repository folder within the vault 选择 `博客`；如果将博客单独打开成一个库，则留空。
- GitHub 仓库 Settings → Pages → Build and deployment → Source 选择 **GitHub Actions**，而不是 Deploy from a branch。
- 工作流文件是 `.github/workflows/pages.yml`，名称是 **Build and deploy blog**。推送 main 分支后，build 和 deploy 都成功才算网页更新完成。

## 2. 日常工作流

```text
Obsidian 编辑 content 中的 Markdown
→ 保存
→ Git Source Control 检查本次新增、修改、删除
→ 填写提交说明
→ Commit-and-sync（包含推送），或分别 Commit、Push
→ GitHub Actions 验证、构建、部署
→ 刷新网站确认
```

| 环节 | 判断是否完成 |
|---|---|
| 保存 | Obsidian 中的文件内容已改变 |
| 暂存 Stage | 选定的文件出现在 Staged Changes |
| 提交 Commit | 版本已保存在本机；这一步尚未上传 |
| 推送 Push | GitHub Code 中出现最新提交 |
| 构建与部署 | Actions 中最新的 Build and deploy blog 显示绿色成功 |
| 网页检查 | 标题、摘要、正文、标签和分类显示符合预期 |

**Changes 为 0 只代表没有未提交改动，不代表推送或部署成功。** Commit-and-sync 会处理整个博客仓库的改动；只想发布部分文件时，先单独暂存它们，再选择 Commit staged，随后 Push。若使用 Commit-and-sync，确认插件的 Push on commit-and-sync 已开启。

提交说明可以写「新增：国庆随记」「修改：散步的摘要和标签」「删除：测试文章」。开始阶段建议手动同步，熟悉后再考虑定时自动提交。

## 3. 新增笔记：推荐使用模板

1. Obsidian 设置 → 核心插件，启用 **Templates（模板）**。
2. 模板设置 → Template folder location，选择 `博客/templates`。独立打开博客库时选择 `templates`。
3. 在 `博客/content` 第一层创建笔记，例如 `walk-in-wind.md`。不要放到它的子文件夹中。
4. Ctrl+P → **Templates: Insert template** → 选择 `new-post`。
5. 编辑开头属性，阅读模板正文中的填写提示；完成后用自己的正文替换提示。
6. 保持 `draft: true` 进行整理；准备展示时改成 `draft: false`，然后提交并推送。

插入模板会自动填写当天 updated 日期；直接复制模板文件不会替换日期占位符，需手动改为真实的 `YYYY-MM-DD` 日期。

### 文件名和文章网址

- 文件名只用小写英文字母、数字、连字符，例如 `walk-in-wind.md`、`2026-10-3.md`。
- 网页显示的中文标题写在 title 中，不必与文件名相同。
- slug 可以省略，程序默认使用文件名去掉 `.md`；若填写，必须与文件名完全一致。
- 所有文章详情页统一使用 `/essays/文件名/`，即使分类是短记、摘录或专题整理。
- 已发布的文件名和 slug 尽量保持不变。修改 title 不会改变网址；改文件名会改变网址，目前不自动生成旧网址跳转。

例如 `content/walk-in-wind.md` 的详情地址是：

`https://4444hao.github.io/essays/walk-in-wind/`

### 可复制的最小文章示例

**只复制代码框内部的内容。实际文件第一行必须是 `---`，不要把外层的三个反引号或 markdown/yaml 字样复制进去。** 以下日期只是格式示例，写作时改为实际日期。

```markdown
---
title: 风中的散步
category: 随笔
tags:
  - 自然
  - 独处
summary: 一次散步，让我重新留意到树影和自己的节奏。
updated: '2026-10-03'
draft: true
provenance: 个人记录
sourceNote: 个人记录。
---

这里替换为自己的正文。
```

## 4. 属性怎么填写

| 属性 | 必填或默认 | 填写说明 |
|---|---|---|
| title | 必填 | 展示标题，可使用中文 |
| category | 必填 | 只选随笔、短记、摘录、专题整理中的一个 |
| tags | 建议填写列表 | 通常 2–3 个，最多 4 个是写作建议，不是程序限制；允许为空列表 `[]` |
| summary | 必填 | 一句摘要，用于列表；尽量说明这篇在写什么，不复制整段正文 |
| updated | 必填 | 本次内容维护日期，格式 `YYYY-MM-DD`，如 `2026-10-03` |
| draft | 默认 false；模板为 true | 只能写布尔值 true 或 false，不用 1/0，也不加引号 |
| provenance | 默认个人记录 | 内容身份，如个人记录、摘录、AI 协助整理；与 category 分开判断 |
| sourceNote | 建议填写 | 来源、作者、链接或整理方式；来源不清写来源待核 |
| slug | 可省略 | 省略时取文件名；填写时与文件名一致，不写完整网址或带空格的句子 |
| date | 可选 | 确定的原始写作日期；未知不填，不把摘录录入日当作原作日期 |
| order | 可选 | 整数；用于同日期或无日期文章的固定顺序，通常不需要改 |

### 四个分类怎么选

| 分类 | 适合的内容 | 判断参考 |
|---|---|---|
| 随笔 | 相对展开的经历、感受、思考 | 围绕一件事或一个问题，有自己的叙述与展开 |
| 短记 | 一小段观察、念头、片刻记录 | 篇幅短，先记下，不必补成完整长文 |
| 摘录 | 收藏的句子、段落、观点 | 重点来自他人文本，可附自己的理解，并说明来源 |
| 专题整理 | 围绕主题汇集、梳理的资料和想法 | 有结构，可继续增补，不要求已经完成 |

分类不等于原创身份；专题整理也可能含摘录或 AI 协助内容，需要单独填写来源说明。

### 标签待选参考

自然、动物、日常、回忆、独处、情绪、关系、选择、意义、阅读、学习、行动。

可以增加「思考与选择」等更贴切的标签。优先沿用已有标签表达共同主题，再补一个能突出这篇特点的标签；避免给每篇堆上全部标签，也避免同一含义反复造不同名称。tags 使用列表，冒号后换行，每项前有两个空格和 `- `。

标签无需维护固定白名单。公开文章中的新标签会自动进入图谱，引用篇数越多节点越大；两标签共同出现在同一篇文章中，就会形成联系。

## 5. 新文章会出现在网站哪里

`draft: false` 且成功部署后，文章会同时进入**主页的全部笔记列表**和**所属分类的列表**。

| category | 所属栏目 | 列表地址 |
|---|---|---|
| 随笔 | 随笔 | `/essays/` |
| 短记 | 短记 | `/notes/` |
| 摘录 | 摘录 | `/excerpts/` |
| 专题整理 | 专题整理 | `/collections/` |

- 列表显示标题、一句摘要、该篇标签和分类；每页 10 篇，页数随文章量变化。
- 标签图谱只在主页。点击某个标签，会筛选出带该标签的公开文章。
- 主页文章数量、正文总字数和最近内容更新时间由公开文章汇总；字数包含摘录，不计入草稿。
- 有 date 的文章按写作日期倒序，无日期的文章放后面。日期相同时或无日期时，按 order、文件名保持固定顺序。
- **updated 只表示维护日期，不会把文章置顶。** 新文章如果希望按已知写作日期排入前面，可填写 date；未知日期就省略。由于分页，不一定在第一页看到新增文章。

`draft: true` 不生成详情页，不进入列表、统计或图谱。但提交到公开 GitHub 仓库后，草稿源文件仍能被读取；私人内容放在博客仓库之外。

## 6. 修改、删除和撤下

- **修改正文或属性**：直接编辑对应 Markdown，更新 updated，检查后提交并推送。不要修改生成的 HTML。
- **改分类**：修改 category 后，下一次成功部署会从原栏目移入新栏目；详情网址不变。
- **改标签**：修改 tags 后，自动更新筛选和图谱。最后一篇引用某标签的文章撤下或删除后，该标签消失。
- **删除文章**：删除 content 中的 Markdown，确认 Git 中有这条删除记录，再提交并推送。成功部署后对应网页、列表条目和统计一起移除。
- **暂时撤下**：把 draft 改为 true，再提交并推送。之后改回 false 可以重新展示。
- 删除或撤下不抹除 Git 历史；已发布的旧网址会失效，目前没有自动重定向。

## 7. 正文注意事项

支持标题、段落、列表、引用、表格、代码块和本地图片。正文建议从二级标题开始，文章 title 已作为页面大标题。

- 摘录用引用块，并补作者、作品或链接；缺失来源注明来源待核。
- AI 协助内容在 provenance/sourceNote 说明协助范围。
- Obsidian 双链和图片嵌入需转成标准 Markdown；当前构建不支持 `[[笔记]]` 和 `![[图片]]`。
- 代码围栏只用于正文中的局部代码，不包住整篇文章和开头属性。
- Mermaid 第一版按代码块展示，不生成图；原始 HTML 会转义，不执行。
- 图片放进 `assets/images/`，网站使用 `![说明](/assets/images/tree.webp)`。要把图片文件与文章一起推送；此站点根路径在 Obsidian 中可能无法预览。
- 文章间链接可使用 `[另一篇文章](/essays/另一篇的英文文件名/)`。删除目标文章前检查相关链接。

## 8. 发布前检查

- [ ] 文件在 content 第一层，第一行是 `---`，属性之后有第二个 `---`。
- [ ] 文件名符合要求，若有 slug，它与文件名一致。
- [ ] 标题、摘要和正文已填写，模板中的提示文字已删除。
- [ ] 分类正确，标签没有重复堆叠，来源说明准确。
- [ ] updated 是本次维护日期；date 仅在写作日期确定时填写。
- [ ] 要展示时 draft 是 false；暂无展示意图时保持 true。
- [ ] Source Control 中检查了本次新增、修改、删除；图片也包含在本次同步中。
- [ ] 推送后确认 Actions 的 build、deploy 都成功，再检查线上页面。

## 9. 出错时看哪里

| 现象 | 优先检查 |
|---|---|
| GitHub 没有最新内容 | 是否只 Commit，没有 Push；推送是否报错 |
| GitHub 更新了，网页没更新 | Pages Source 是否 GitHub Actions；最新工作流是否成功 |
| missing YAML front matter | 文件第一行不是 `---`，或整篇被包在代码围栏里 |
| filename must match slug | 文件名和 slug 不一致 |
| Invalid manifest entry | 文件名字符、分类或必填属性不符合要求 |
| draft must be boolean | draft 写成数字或带引号的字符串 |
| 日期错误 | 使用了 `2026-10-3` 等不完整日期，或未替换模板日期占位符 |
| Resolve Obsidian links | 正文残留 Obsidian 双链 |
| 新文章找不到 | 是否仍为草稿、在后面的分页，或进入了另一个分类 |

构建失败时不会部署，线上保留上一次成功发布的版本。打开 GitHub Actions 中失败运行，展开失败步骤读取具体错误；修正文件后重新提交并推送，仅刷新网页不能修正构建错误。

## 10. 目录与可选本地预览

| 位置 | 用途 |
|---|---|
| content/*.md | 日常维护的文章源文件 |
| templates/new-post.md | Obsidian 新文章模板 |
| README.md | 本工作流与填写参考 |
| OBSIDIAN_WORKFLOW.md | 简版 Obsidian 操作说明 |
| assets/ | 图片、样式、脚本 |
| site.json | 网站名、简介、网址、分类配置 |
| .github/workflows/pages.yml | GitHub 自动验证、构建与部署 |
| docs/ | 生成的网页，不直接编辑 |
| content/index.json | 生成的内容索引，不在这里修改文章属性 |

Actions 构建结果作为网页产物直接部署，**不回写源码分支中的 docs 和 index.json**；因此仓库里旧的生成文件可能与最新线上内容不同，日常只维护源文件即可。

需要本地预览时，在 VS Code 打开本仓库，首次安装依赖：

```powershell
python -m pip install -r requirements.txt
```

Ctrl+Shift+B 构建，再运行「预览博客（8001）」任务；或在终端分别执行：

```powershell
python build.py
python -m http.server 8001 --bind 127.0.0.1 --directory docs
```

浏览器打开 http://127.0.0.1:8001/，不要直接双击 HTML。停止服务按 Ctrl+C。
