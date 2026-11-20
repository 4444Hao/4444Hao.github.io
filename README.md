# 走心旁白 · 目录与维护地图

[博客首页](https://4444hao.github.io/) · [GitHub 仓库](https://github.com/4444Hao/4444Hao.github.io) · [RSS](https://4444hao.github.io/feed.xml)

**唯一维护目录：** `D:\obsidian笔记\obsidian4444\博客`。本机的文件修改和生成仅在这个目录内进行，预览、截图和临时产物也放在目录内。日常编辑以这里的 Markdown、配置和源码为准；`docs/` 和 `content/index.json` 是构建产物。

## 完整目录树

下图列出仓库里的维护入口及构建输出。文章、分页、缓存等重复项按路径模式列出，不逐个展开。

```text
博客/
├── README.md                       本文件：目录地图、编辑入口、发布路线
├── OBSIDIAN_WORKFLOW.md             Obsidian 写作、预览、同步和排错步骤
├── CONTENT_REVIEW.md                初版内容审阅记录，所列篇数是历史快照
├── git-test.md                      早期 Obsidian Git 提交测试，不生成网页
├── site.json                        站名、首页主标题、网址、分类配置与简介
├── build.py                         构建入口：读取笔记、套用模板、生成网页和 RSS
├── requirements.txt                 Python 依赖清单，目前为 PyYAML
├── .gitignore                       Git 忽略规则，包括本地草稿和缓存
├── .github/
│   └── workflows/
│       └── pages.yml                推送到 main 后验证、构建并部署；也可手动触发
├── .vscode/
│   └── tasks.json                   VS Code 构建和本地预览任务（端口 8001）
├── assets/                          网站资源源码
│   ├── style.css                    字体、基础配色、正文、表格和文章排版
│   ├── graph.css                    白页外框、浅灰绿顶栏、左栏双列栏目、图谱和分页样式
│   ├── graph.js                     图谱排布、拖动、连线高亮和视图切换
│   ├── filter.js                    标签筛选、笔记列表和分页交互
│   ├── favicon.svg                  页眉标志和浏览器标签页图标
│   ├── header-grass.svg             宽屏顶栏的风吹草木剪影
│   ├── wind-in-trees.webp           首页树木插图
│   └── paper-grain.svg              原版纸纹资源；当前白页外框不使用这层纸纹
├── content/
│   ├── *.md                         笔记原文与属性，构建只读取这一层的 Markdown
│   └── index.json                   自动生成的笔记索引，不手改
├── drafts/                          本地草稿，Git 忽略，构建不读取
├── templates/
│   └── new-post.md                  Obsidian 的新笔记模板，不直接生成网页
├── tests/
│   ├── test_build.py                验证链接、图谱、草稿、RSS、分页和时间排序
│   └── __pycache__/                 Python 测试缓存（本地）
├── docs/                            自动生成的静态站点；部署只上传此目录
│   ├── index.html                   首页 /
│   ├── about/index.html             关于页 /about/
│   ├── all/index.html               全部笔记 /all/
│   ├── essays/
│   │   ├── index.html               随笔栏目 /essays/
│   │   └── <文章文件名>/index.html    所有分类的文章详情统一放在这里
│   ├── notes/index.html             短记栏目 /notes/
│   ├── excerpts/index.html          摘录栏目 /excerpts/
│   ├── collections/index.html       专题整理栏目 /collections/
│   ├── 各列表下的 page/<页码>/index.html   列表有多页时生成后续分页
│   ├── page/<页码>/index.html        旧分页网址的跳转页
│   ├── assets/
│   │   ├── graph-data.json          标签和连线数据，从公开笔记计算
│   │   └── 其他文件                  根目录 assets/ 的构建副本
│   ├── feed.xml                     RSS 订阅源
│   ├── sitemap.xml                  网站地图
│   ├── robots.txt                   搜索引擎抓取规则和站点地图地址
│   ├── 404.html                     找不到页面时的提示
│   └── .nojekyll                    告诉 GitHub Pages 无需用 Jekyll 处理这些静态文件
├── .preview/                       可选的仓库内预览与截图目录，按需创建，已忽略
├── .git/                            Git 内部数据，不直接编辑
├── __pycache__/                      Python 本地缓存，已忽略
└── node_modules/                    本地工具依赖，已忽略；线上构建不依赖它
```

## 想改哪里，就打开哪个文件

| 想修改的内容 | 编辑入口 |
| --- | --- |
| 文章标题、摘要、分类、标签、日期和正文 | `content/对应笔记.md`。开头两道 `---` 之间是属性。修订时更新 `updated`。 |
| 草稿与新笔记模板 | 草稿写在 `drafts/`，模板改 [templates/new-post.md](templates/new-post.md)。 |
| 站名「走心旁白」、首页大标题「我的文字与记录」、分类标题下的小字 | [site.json](site.json) 的 `title`、`description`、`sectionDescriptions`。 |
| 「关于这里」「你好。」、关于页介绍、页脚短句或栏目导航 | [build.py](build.py)。关于页搜索 `about=`；左栏顺序、窄屏顶部导航、站名链接和页脚在 `page()`。 |
| 首页标题下的介绍、统计栏文字、「最近笔记」标题 | [build.py](build.py)，分别找 `intro-line`、`site-stats` 和 `recent_listing()`。篇数、字数、更新时间由构建计算。 |
| 页面宽度、顶栏颜色、桌面左栏、图谱配色与手机断点 | [assets/graph.css](assets/graph.css)。外框找 `.notebook-shell`，顶栏找 `.site-chrome`，左栏和栏目网格找 `.site-sidebar`、`.sidebar-links nav`。 |
| 字体、正文颜色与行距、引用、表格、代码块 | [assets/style.css](assets/style.css)。基础字体和颜色找 `:root`，正文找 `.prose`；`graph.css` 后加载，可能覆盖部分规则。 |
| 页眉标志、顶栏草木、首页插画 | 分别改 [favicon.svg](assets/favicon.svg)、[header-grass.svg](assets/header-grass.svg)、[wind-in-trees.webp](assets/wind-in-trees.webp)。顶栏的 RSS 链接在 `build.py` 的 `page()`。 |
| 图谱排布、拖动手感、标签点击后的筛选 | 排布与拖动看 [graph.js](assets/graph.js)，筛选与分页看 [filter.js](assets/filter.js)。新增标签只需改笔记的 `tags`。 |
| 首页几篇、列表每页几篇、RSS 保留多少条 | [build.py](build.py) 中的 `RECENT_SIZE`、`PAGE_SIZE`、`RSS_SIZE`，当前分别为 6、10、20。 |
| 本地预览命令、部署触发条件 | 分别看 [.vscode/tasks.json](.vscode/tasks.json) 和 [.github/workflows/pages.yml](.github/workflows/pages.yml)。 |

**改源码，再看产物。** 例如要改样式，编辑根目录 `assets/` 下的 CSS；直接改 `docs/assets/` 里的副本，下次构建会覆盖。GitHub Actions 会重新生成 `docs/` 并部署，不会把产物写回源码分支，所以仓库中的旧 `docs/` 不一定等于线上版本。

## 页面怎么布局

- **宽屏（1101 px 起）：** 浅灰绿顶栏铺一层淡草木剪影，左侧是站名，右侧是「RSS 订阅」。左栏从上到下是双列栏目、文章标签和关于本站。首页默认展开图谱，右侧显示按 `updated` 倒序排列的最近 6 篇公开笔记。文章页左栏会随滚动吸顶，图谱默认收起。
- **手机和窄窗口：** 顶栏使用浅灰绿纯色，保留栏目导航和 RSS 入口。首页依次显示介绍、图谱、最近笔记，内页不显示侧栏。

## 写作、预览与发布

本地草稿写在 `drafts/` → 确认要公开时检查属性、将 `draft` 改成 `false` 并移入 `content/` → 在 Obsidian Git 检查新增、修改和删除 → Commit-and-sync → 在 GitHub Actions 确认构建与部署成功。

- **文件名决定文章链接。** 例如 `content/walk-in-wind.md` 对应 `/essays/walk-in-wind/`；改分类可换栏目，改文件名会换链接。
- **草稿只在本地。** `drafts/` 不随 Git 同步，换电脑可手动新建。放进 `content/` 后，即使设为 `draft: true`，也只是不上网页和 RSS；提交到公开仓库的源文件仍可见。忽略规则对已经跟踪的文件和 Git 历史不追溯生效。
- **RSS 随网站更新。** 公开笔记按 `updated` 倒序进入最近 20 条，包含标题、摘要、链接等，无需 `published`。订阅工具在下次拉取后显示变化；修订旧文不一定再提醒。
- **本地预览可选。** 在 VS Code 打开博客目录，运行任务「预览博客（8001）」。它会先在本目录构建 `docs/`，再提供 [本地预览](http://127.0.0.1:8001/)。日常发布无需在本机先构建。
- **预览附件和临时产物。** 如需额外保存截图或临时构建副本，可在本仓库内使用已被 Git 忽略的 `.preview/`；不把这些产物放到其他本地目录。

更详细的新增、删除、附件与构建排错见 [Obsidian 维护工作流](OBSIDIAN_WORKFLOW.md)。
