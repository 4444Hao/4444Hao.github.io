"""Build a quiet Markdown blog into docs/ for static hosting."""
from __future__ import annotations

import argparse
import unicodedata
import math
from collections import Counter
from itertools import combinations
try:
    import yaml
except ModuleNotFoundError:
    raise SystemExit('缺少 PyYAML，请先运行：python -m pip install -r requirements.txt')
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse, quote

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs"
SITE = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
def load_notes():
    """Markdown front matter is authoritative; index.json is generated for review."""
    notes, content = [], {}
    for file in sorted((ROOT / 'content').glob('*.md')):
        raw = file.read_text(encoding='utf-8-sig')
        match = re.match(r'\A---\s*\n(.*?)\n---\s*\n(.*)\Z', raw, re.S)
        if not match: raise ValueError(f'{file.name}: missing YAML front matter')
        n = yaml.safe_load(match[1])
        if not isinstance(n, dict): raise ValueError(f'{file.name}: front matter must be a mapping')
        n['slug'] = n.get('slug', file.stem)
        if n['slug'] != file.stem: raise ValueError(f'{file.name}: filename must match slug')
        for key in ('title', 'category', 'summary', 'updated'):
            if not n.get(key): raise ValueError(f'{file.name}: missing {key}')
        n['excerpt'] = str(n.pop('summary'))
        n['updatedAt'] = str(n.pop('updated'))
        if n.get('date'): n['date'] = str(n['date'])
        else: n.pop('date', None)
        n.setdefault('draft', False)
        n.setdefault('provenance', '个人记录')
        n.setdefault('sourceNote', '个人记录。' if n['provenance']=='个人记录' else '来源待核。')
        tags = n.get('tags', [])
        if not isinstance(tags, list) or any(not isinstance(t, str) or not t.strip() for t in tags):
            raise ValueError(f'{file.name}: tags must be a list of nonempty strings')
        n['tags'] = list(dict.fromkeys(t.strip().lstrip('#') for t in tags))
        if any(not t or len(t)>40 or any(ord(c)<32 for c in t) for t in n['tags']):
            raise ValueError(f'{file.name}: invalid tag')
        if not isinstance(n.get('order', 1000000), int): raise ValueError(f'{file.name}: order must be an integer')
        notes.append(n); content[n['slug']] = match[2].strip() + '\n'
    notes.sort(key=lambda n: (n.get('order',1000000),n['slug']))
    return notes, content


MANIFEST, CONTENT = load_notes()
CATEGORIES = SITE["categories"]
ORIGIN = SITE["url"].rstrip("/")
PAGE_SIZE = 10
RECENT_SIZE = 6
ALL_BASE = "/all/"
SECTIONS = {'随笔':'/essays/', '短记':'/notes/', '摘录':'/excerpts/', '专题整理':'/collections/'}


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def safe_url(value: str, image: bool = False) -> str:
    value = value.strip()
    if any(ord(char) < 32 for char in value) or value.startswith("//"):
        raise ValueError(f"Unsupported URL: {value!r}")
    scheme = urlparse(value).scheme.lower()
    allowed = ("",) if image else ("", "https", "http", "mailto")
    if scheme not in allowed:
        raise ValueError(f"Unsupported URL scheme: {value!r}")
    if value.lower().startswith("javascript:"):
        raise ValueError("Unsafe URL")
    return esc(value)


def inline(text: str) -> str:
    """Small safe Markdown subset; HTML stays escaped, no scripts or embeds."""
    tokens: list[str] = []

    def stash(markup: str) -> str:
        tokens.append(markup)
        return f"\x00{len(tokens) - 1}\x00"

    text = re.sub(r"`([^`]+)`", lambda m: stash(f"<code>{esc(m[1])}</code>"), text)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^\s)]+)\)",
        lambda m: stash(f'<img src="{safe_url(m[2], image=True)}" alt="{esc(m[1])}" loading="lazy" decoding="async">'),
        text,
    )
    text = re.sub(
        r"(?<!!)\[([^\]]+)\]\(([^\s)]+)\)",
        lambda m: stash(f'<a href="{safe_url(m[2])}">{esc(m[1])}</a>'),
        text,
    )
    text = esc(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    for index, markup in enumerate(tokens):
        text = text.replace(f"\x00{index}\x00", markup)
    return text


def markdown(text: str) -> str:
    """Paragraphs, hard line breaks, headings, lists, quotes and fenced code."""
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_kind: str | None = None
    code: list[str] | None = None
    quotes: list[str] = []

    def flush() -> None:
        nonlocal list_kind
        if paragraph:
            blocks.append("<p>" + "<br>\n".join(inline(line) for line in paragraph) + "</p>")
            paragraph.clear()
        if list_items:
            blocks.append(f"<{list_kind}>" + "".join(f"<li>{inline(item)}</li>" for item in list_items) + f"</{list_kind}>")
            list_items.clear()
            list_kind = None
        if quotes:
            blocks.append("<blockquote><p>" + "<br>".join(inline(line) for line in quotes) + "</p></blockquote>")
            quotes.clear()

    # Parse pipe tables before ordinary block processing; raw HTML remains escaped.
    lines = text.splitlines()
    prepared = []
    tables = []
    pos = 0
    fenced = False
    def cells(line):
        return re.split(r"(?<!\\)\|", line.strip().strip("|"))
    while pos < len(lines):
        if lines[pos].strip().startswith("```"):
            fenced = not fenced
        if not fenced and pos + 1 < len(lines) and "|" in lines[pos] and all(
            re.fullmatch(r"\s*:?-{3,}:?\s*", cell) for cell in cells(lines[pos+1])):
            header = cells(lines[pos]); rows = []; pos += 2
            while pos < len(lines) and "|" in lines[pos] and lines[pos].strip():
                rows.append(cells(lines[pos])); pos += 1
            tables.append('<div class="table-scroll" role="region" aria-label="文章表格" tabindex="0"><table><thead><tr>' +
                ''.join('<th scope="col">'+inline(cell.strip())+'</th>' for cell in header) + '</tr></thead><tbody>' +
                ''.join('<tr>'+''.join('<td>'+inline(cell.strip())+'</td>' for cell in row)+'</tr>' for row in rows) +
                '</tbody></table></div>')
            prepared.append(f"\x01{len(tables)-1}\x01")
            continue
        prepared.append(lines[pos]); pos += 1
    heading_ids = {}
    for raw in prepared:
        line = raw.strip()
        if line.startswith("```"):
            if code is None:
                flush()
                code = []
            else:
                blocks.append("<pre><code>" + esc("\n".join(code)) + "</code></pre>")
                code = None
            continue
        if code is not None:
            code.append(raw)
            continue
        if line.startswith("\x01"):
            flush()
            blocks.append(tables[int(line.strip("\x01"))])
            continue
        if re.fullmatch(r"([-*_])(?:\s*\1){2,}", line):
            flush()
            blocks.append("<hr>")
            continue
        if not line:
            flush()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        item = re.match(r"^([-*+]\s+|\d+\.\s+)(.+)$", line)
        if heading:
            flush()
            level = min(len(heading[1]) + 1, 6)
            anchor = re.sub(r"[^\w\- ]", "", re.sub(r"[*`]", "", heading[2])).lower().replace(" ", "-")
            count = heading_ids.get(anchor, 0); heading_ids[anchor] = count + 1
            anchor = anchor + (f"-{count}" if count else "")
            blocks.append(f'<h{level} id="{esc(anchor)}">{inline(heading[2])}</h{level}>')
        elif line.startswith("> "):
            if paragraph or list_items:
                flush()
            quotes.append(line[2:])
        elif item:
            kind = "ol" if item[1][0].isdigit() else "ul"
            if paragraph or quotes or (list_kind is not None and list_kind != kind):
                flush()
            list_kind = kind
            list_items.append(item[2])
        else:
            if list_items or quotes:
                flush()
            paragraph.append(line)
    if code is not None:
        raise ValueError("Unclosed Markdown code fence")
    flush()
    return "\n".join(blocks)


def write(path: str, content: str) -> None:
    destination = OUT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8", newline="\n")


def page(title: str, body: str, *, current: str, path: str, description: str = "", article: bool = False, toolbar: str = "") -> str:
    full_title = SITE["title"] if not title else f'{title} · {SITE["title"]}'
    nav = []
    for key, label, href in (("home", "主页", "/"), ("随笔", "随笔", "/essays/"), ("短记", "短记", "/notes/"), ("摘录", "摘录", "/excerpts/"), ("专题整理", "专题整理", "/collections/")):
        state = ' aria-current="page"' if key == current else ""
        nav.append(f'<a href="{href}"{state}>{label}</a>')
    desc = description or SITE["description"]
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(full_title)}</title>
  <meta name="description" content="{esc(desc)}">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'">
  <meta name="theme-color" content="#f7f6ef">
  <link rel="canonical" href="{esc(ORIGIN + path)}">
  <meta property="og:title" content="{esc(full_title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:type" content="{'article' if article else 'website'}">
  <meta property="og:url" content="{esc(ORIGIN + path)}">
  <link rel="icon" type="image/svg+xml" href="/assets/favicon.svg?v=wind-voice">
  <link rel="stylesheet" href="/assets/style.css">
  <link rel="stylesheet" href="/assets/graph.css">
<script src="/assets/filter.js" defer></script>
<script src="/assets/graph.js" defer></script>
</head>
<body>
  <a class="skip-link" href="#main">跳到正文</a>
  <div class="notebook-shell">
  <div class="site-chrome"><header class="site-header wrap">
    <a class="brand" href="/about/" aria-label="关于{esc(SITE['title'])}"><img class="brand-mark" src="/assets/favicon.svg?v=wind-voice" width="32" height="32" alt="" aria-hidden="true"><span>{esc(SITE['title'])}</span></a>
    <nav aria-label="主要导航">{''.join(nav)}</nav>
  </header>{toolbar}</div>
  <main id="main" class="wrap {'reading-main' if article else ''}">{body}</main>
  <footer class="site-footer wrap"><span>走心地旁白</span><nav aria-label="页脚导航"><a href="/about/">关于</a><a href="{esc(SITE['github'])}">GitHub</a></nav></footer>
  </div>
</body>
</html>
'''


def tag_links(note: dict) -> str:
    return '<div class="entry-tags">' + ''.join(f'<a href="/all/?tag={quote(tag)}#records">{esc(tag)}</a>' for tag in note['tags']) + '</div>'


def updated_time(value: str) -> datetime:
    value = str(value)
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=timezone(timedelta(hours=8))) if parsed.tzinfo is None else parsed


def updated_label(value: str) -> str:
    stamp = updated_time(value).astimezone(timezone(timedelta(hours=8)))
    return stamp.strftime('%Y-%m-%d %H:%M') if len(str(value)) > 10 else stamp.strftime('%Y-%m-%d')


def note_time(note: dict) -> str:
    updated = f'<span>更新于 <time datetime="{esc(note["updatedAt"])}">{esc(updated_label(note["updatedAt"]))}</time></span>'
    if not note.get('date'):
        return f'<div class="note-time">{updated}</div>'
    written = f'<span>写于 <time datetime="{esc(note["date"])}">{esc(note["date"])}</time></span>'
    return f'<div class="note-time">{written}{updated if note["date"] != note["updatedAt"] else ""}</div>'


def recent_listing(notes: list[dict]) -> str:
    return f'''<section id="records" class="records recent-records" data-kind="recent" aria-labelledby="records-title">
    <header class="section-heading"><div><h2 id="records-title">最近笔记</h2><p id="list-summary">按最近内容更新时间排列，包含修订过的笔记。</p></div><a class="more-notes" href="/all/#records">查看全部 →</a></header>
    <ul class="essay-list">{''.join(entry(n) for n in notes[:RECENT_SIZE])}</ul>
{'' if notes else '<p class="empty-results">还没有公开笔记。</p>'}
    </section>'''


def entry(note: dict) -> str:
    return f"""<li class="essay-entry" data-slug="{esc(note['slug'])}" data-updated="{esc(note['updatedAt'])}" data-category="{esc(note['category'])}" data-tags="{esc(json.dumps(note['tags'], ensure_ascii=False))}">
    <div class="entry-top"><a class="essay-link" href="/essays/{esc(note['slug'])}/"><h3>{esc(note['title'])}</h3></a><span class="entry-category">{esc(note['category'])}</span></div>
    <p class="entry-excerpt">{esc(note['excerpt'])}</p>{tag_links(note)}{note_time(note)}</li>"""


def listing_path(base: str, number: int) -> str:
    return base if number == 1 else f'{base}page/{number}/'


def pager(total: int, number: int, base: str) -> str:
    pages = max(1, math.ceil(total / PAGE_SIZE))
    def link(target, label, kind='', rel=''):
        relation = f' rel="{rel}"' if rel else ''
        return f'<a class="{kind}" data-page="{target}" href="{listing_path(base,target)}#records"{relation}>{label}</a>'
    previous = link(number-1, '上一页', 'pager-step', 'prev') if number>1 else '<span class="pager-step" aria-disabled="true">上一页</span>'
    following = link(number+1, '下一页', 'pager-step', 'next') if number<pages else '<span class="pager-step" aria-disabled="true">下一页</span>'
    numbers = []
    chosen = sorted({1, pages, *range(max(1,number-2),min(pages,number+2)+1)})
    last = 0
    for i in chosen:
        if last and i-last>1: numbers.append('<span class="page-gap" aria-hidden="true">…</span>')
        numbers.append(f'<span class="page-number" aria-current="page">{i}</span>' if i==number else link(i,str(i),'page-number'))
        last = i
    return f'<nav id="pagination" class="pagination" aria-label="笔记分页"{(" hidden" if pages==1 else "")}>'+previous+f'<div class="page-numbers">{"".join(numbers)}</div><span class="page-indicator">第 {number} / {pages} 页</span>'+following+'</nav>'


def listing(notes: list[dict], *, page_number=1, title='全部笔记', base='/', home=False, kind='section') -> str:
    total=len(notes); pages=max(1,math.ceil(total/PAGE_SIZE))
    portion=notes[(page_number-1)*PAGE_SIZE:page_number*PAGE_SIZE]
    heading = 'h2' if home else 'h1'
    extra = '<a class="back-to-graph" href="#topics-title">回到图谱 ↑</a>' if home else ''
    intro = SITE.get('sectionDescriptions', {}).get(title, '')
    intro_html = f'<p class="listing-intro">{esc(intro)}</p>' if intro else ''
    return f"""<section id="records" class="records{' section-listing' if not home else ''}" aria-labelledby="records-title" data-kind="{kind}" data-base="{base}" data-page="{page_number}" data-page-size="{PAGE_SIZE}">
    <header class="{'section-heading' if home else 'listing-heading'}"><div><{heading} id="records-title" tabindex="-1">{esc(title)}</{heading}>{intro_html}<p id="list-summary" role="status" aria-live="polite">按最近更新排列 · 共 {total} 篇 · 第 {page_number} / {pages} 页</p></div>{extra}</header>
    <ul class="essay-list">{''.join(entry(n) for n in portion)}</ul>
    <div id="empty-results" class="empty-results" hidden><p>这里暂时没有符合条件的笔记。</p><button type="button" id="empty-clear">查看全部笔记</button></div>{pager(total,page_number,base)}
    <template id="article-catalog">{''.join(entry(n) for n in notes)}</template></section>"""


class BodyText(HTMLParser):
    def __init__(self):
        super().__init__(); self.text = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('h1','h2','h3','h4','h5','h6','figcaption','summary'):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('h1','h2','h3','h4','h5','h6','figcaption','summary'):
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip: self.text.append(data)


def word_count(rendered: str) -> int:
    parser = BodyText(); parser.feed(rendered)
    return sum(unicodedata.category(char)[0] in ('L', 'N') for char in ''.join(parser.text))


def build() -> None:
    slugs = [n['slug'] for n in MANIFEST]
    if len(slugs) != len(set(slugs)):
        raise ValueError('Duplicate article slug')
    for n in MANIFEST:
        if not re.fullmatch(r'[a-z0-9-]+', n['slug']) or n['category'] not in CATEGORIES:
            raise ValueError(f'Invalid manifest entry: {n}')
        if not isinstance(n['draft'], bool): raise ValueError('draft must be boolean')
        updated_time(n['updatedAt'])
        if n.get('date'): date.fromisoformat(n['date'])
    notes = sorted([n for n in MANIFEST if not n['draft']], key=lambda n: updated_time(n['updatedAt']), reverse=True)
    # Validate and render before replacing output, so a bad note preserves the last preview.
    rendered = {}
    for n in notes:
        content = CONTENT[n['slug']]
        if re.search(r'\[\[', content): raise ValueError(f'Resolve Obsidian links: {n["slug"]}')
        rendered[n['slug']] = markdown(content)
    total = sum(word_count(body) for body in rendered.values())
    updated = max((n['updatedAt'] for n in notes), key=updated_time) if notes else '暂无'
    if OUT.exists():
        if OUT.is_symlink() or OUT.resolve().parent != ROOT.resolve():
            raise ValueError('Refusing to replace output outside project')
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / 'assets', OUT / 'assets')
    write('.nojekyll', '')
    # All graph counts and relationships come exclusively from non-draft notes.
    counts = Counter(t for n in notes for t in n['tags'])
    cooccurrence = Counter(pair for n in notes for pair in combinations(sorted(n['tags']),2))
    tag_names = sorted(counts, key=lambda t: (-counts[t], t))
    ids = {tag:i for i,tag in enumerate(tag_names)}
    node_markup = []
    for i,tag in enumerate(tag_names):
        radius = min(61, 27 + 5.8 * math.sqrt(counts[tag]))
        display_tag = tag if len(tag) <= 12 else tag[:11] + '…'
        chunks = [display_tag[j:j+4] for j in range(0,len(display_tag),4)]
        label = ''.join(f'<tspan x="0" dy="{0 if j==0 else 16}">{esc(chunk)}</tspan>' for j,chunk in enumerate(chunks))
        label_y = -4 - 8*(len(chunks)-1)
        node_markup.append(f'<g class="graph-node" data-tag="{esc(tag)}" data-count="{counts[tag]}" data-radius="{radius:.2f}" data-node="{i}" role="button" tabindex="0" aria-pressed="false" aria-label="{esc(tag)}，{counts[tag]} 篇文章"><title>{esc(tag)} · {counts[tag]} 篇</title><circle class="node-disc" r="{radius:.2f}"/><text class="node-label" y="{label_y}">{label}</text><text class="node-count" y="{12+8*(len(chunks)-1)}">{counts[tag]} 篇</text></g>')
    lines = ''.join(f'<line data-source="{ids[a]}" data-target="{ids[b]}" data-weight="{weight}" stroke-width="{min(2.2,.45+math.sqrt(weight)*.24):.2f}"/>' for (a,b),weight in sorted(cooccurrence.items()))
    tag_list = ''.join(f'<a class="tag-list-link" data-tag="{esc(tag)}" href="/all/?tag={quote(tag,safe="")}#records" role="button" aria-pressed="false">{esc(tag)}<span>{counts[tag]}</span></a>' for tag in tag_names)
    toolbar='<div class="nav-filters" id="home-filter-status" hidden><div class="filter-status"><span id="filter-description"></span><button type="button" id="remove-tag" aria-label="移除选中的标签" hidden>×</button><span id="result-count"></span><button type="button" id="clear-filters">清除筛选</button></div></div>'
    illustration = '<figure class="landscape"><img src="/assets/wind-in-trees.webp" width="2125" height="740" alt="风中的绿树与安静的草地" decoding="async"></figure>' if (ROOT/'assets/wind-in-trees.webp').exists() else ''
    body=f"""<section class="intro" aria-labelledby="home-title"><div class="intro-copy"><p class="eyebrow">眼所见 · 心所想</p><h1 id="home-title">{esc(SITE['title'])}</h1><p class="intro-line">{esc(SITE['description'])}</p></div><div class="intro-data"><dl class="site-stats"><div><dt>文章</dt><dd>{len(notes)} <small>篇</small></dd></div><div><dt>正文总字数</dt><dd>{total:,} <small>字</small></dd></div><div><dt>最近内容更新</dt><dd><time datetime="{esc(updated)}">{esc(updated_label(updated))}</time></dd></div></dl><p class="count-note">字数包含摘录；标签随公开笔记生长。</p></div></section>
    {illustration}<section class="topics" aria-labelledby="topics-title"><div class="section-heading"><div><p class="eyebrow">话题之间</p><h2 id="topics-title">沿着联系，读下去</h2></div><div class="graph-controls" hidden><button type="button" id="view-graph" aria-pressed="true">图谱</button><button type="button" id="view-list" aria-pressed="false">标签列表</button><button type="button" id="motion-toggle" aria-pressed="false">暂停动态</button></div></div><p class="graph-hint">圆越大，相关记录越多；连线表示共同出现。点击筛选，拖动探索。</p>
    <div id="graph-panel" hidden><svg id="tag-graph" viewBox="0 0 980 420" role="group" aria-label="标签关系图谱" aria-describedby="graph-help"><desc id="graph-help">标签的大小按公开文章篇数计算，连线按标签共同出现的文章篇数计算。使用 Tab 选择标签，Enter 或空格筛选；也可切换标签列表。</desc><defs><radialGradient id="node-fill" cx="32%" cy="25%" r="80%"><stop offset="0%" stop-color="#fafbf3"/><stop offset="100%" stop-color="#dce6d4"/></radialGradient></defs><g class="graph-edges">{lines}</g><g class="graph-nodes">{''.join(node_markup)}</g></svg></div>
    <div id="tag-list" class="tag-list" aria-label="主题标签">{tag_list or '<p>还没有公开标签。</p>'}</div><noscript><p class="count-note">最近笔记显示 6 篇；点击查看全部浏览完整列表。标签筛选需要启用 JavaScript。</p></noscript></section>
    """
    listing_paths=['/']
    write('index.html', page('',body.rstrip()+"\n"+recent_listing(notes),current='home',path='/'))
    for page_number in range(1,max(1,math.ceil(len(notes)/PAGE_SIZE))+1):
        path=listing_path(ALL_BASE,page_number); listing_paths.append(path)
        all_body=listing(notes,page_number=page_number,base=ALL_BASE,kind='all')
        title='全部笔记' if page_number==1 else f'全部笔记 · 第 {page_number} 页'
        write(path.lstrip('/')+'index.html',page(title,all_body,current='home',path=path,toolbar=toolbar))
        if page_number > 1:
            # Keep previously shared list-page addresses useful without changing article URLs.
            target=path+'#records'
            write(f'page/{page_number}/index.html',f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={target}"><link rel="canonical" href="{ORIGIN+path}"><title>全部笔记</title></head><body><a href="{target}">继续浏览全部笔记</a></body></html>')
    write('assets/graph-data.json',json.dumps({'nodes':[{'tag':t,'count':counts[t]} for t in tag_names], 'links':[{'source':a,'target':b,'weight':w} for (a,b),w in sorted(cooccurrence.items())]},ensure_ascii=False,indent=2)+'\n')
    (ROOT/'content/index.json').write_text(json.dumps(MANIFEST,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for category,base in SECTIONS.items():
        section_notes=[n for n in notes if n['category']==category]
        for page_number in range(1,max(1,math.ceil(len(section_notes)/PAGE_SIZE))+1):
            path=listing_path(base,page_number);listing_paths.append(path)
            body=listing(section_notes,page_number=page_number,title=category,base=base)
            title=category if page_number==1 else f'{category} · 第 {page_number} 页'
            write(path.lstrip('/')+'index.html',page(title,body,current=category,path=path))
    for i,n in enumerate(notes):
        stamp = note_time(n)
        neighbors = []
        for offset,label in ((-1,'上一篇'),(1,'下一篇')):
            if 0 <= i+offset < len(notes):
                other=notes[i+offset]
                neighbors.append(f'<a href="/essays/{other["slug"]}/"><span>{label}</span>{esc(other["title"])}</a>')
            else: neighbors.append('<span></span>')
        headings = re.findall(r'<h([2-6]) id="([^"]+)">(.*?)</h\1>', rendered[n['slug']])
        toc = ''
        if len(headings) >= 4 and word_count(rendered[n['slug']]) >= 500:
            toc_links = ''.join(f'<a href="#{anchor}" class="toc-level-{level}">{esc(html.unescape(re.sub(r"<[^>]*>","",label)))}</a>' for level,anchor,label in headings)
            toc = f'<aside class="article-toc"><p>文章目录</p><nav aria-label="文章目录">{toc_links}</nav></aside>'
        section_path=SECTIONS.get(n['category'], '/'); section_label=n['category'] if n['category'] in SECTIONS else '主页'
        category_href=SECTIONS.get(n['category'], '/?category='+quote(n['category'])+'#records')
        body=f"""<div class="reading-layout{' with-toc' if toc else ''}"><article class="essay"><header class="article-heading"><a class="back-link" href="{section_path}#records">返回{section_label}</a><div class="article-meta"><a href="{category_href}">{esc(n['category'])}</a>{stamp}</div><h1>{esc(n['title'])}</h1>{tag_links(n)}<p class="source-note"><strong>{esc(n['provenance'])}</strong> · {esc(n['sourceNote'])}</p></header><div class="prose">{rendered[n['slug']]}</div><p class="maintenance-date">内容整理更新：{esc(updated_label(n['updatedAt']))}</p><nav class="essay-neighbors" aria-label="相邻记录">{''.join(neighbors)}</nav></article>{toc}</div>"""
        write(f'essays/{n["slug"]}/index.html', page(n['title'],body,current=n['category'] if n['category'] in SECTIONS else 'home',path=f'/essays/{n["slug"]}/',description=n['excerpt'],article=True))
    about='<article class="about essay"><header class="page-heading"><p class="eyebrow">关于这里</p><h1>你好。</h1></header><div class="prose"><p>这是一个主要由 GPT-6.1 Sol 搭建完成的个人博客。</p><p>使用 Obsidian + Git 插件维护内容，GitHub Pages 静态托管，GitHub Actions 自动构建与部署。</p></div></article>'
    write('about/index.html',page('关于',about,current='about',path='/about/'))
    write('404.html',page('没有找到这页','<section class="page-heading"><h1>这页暂时不在这里。</h1><p><a href="/">回到首页</a></p></section>',current='',path='/404.html'))
    paths=listing_paths+['/about/']+[f'/essays/{n["slug"]}/' for n in notes]
    write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{esc(ORIGIN+path)}</loc></url>' for path in paths)+'</urlset>\n')
    write('robots.txt',f'User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n')
    print(f'Built {len(notes)} articles; {total} body characters; updated {updated}.')


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
