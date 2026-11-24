"""Build validation uses an isolated copy, so it never touches real notes."""
import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from email.utils import parsedate_to_datetime
from collections import Counter
from html.parser import HTMLParser
from itertools import combinations
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
import yaml

ROOT=Path(__file__).resolve().parents[1]

class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.ids=set(); self.in_template=False; self.entries=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='template':self.in_template=True
        if tag=='li' and 'essay-entry' in attrs.get('class','') and not self.in_template:self.entries.append(attrs)
        if 'id' in attrs:self.ids.add(attrs['id'])
        for key in ('src','href'):
            if key in attrs:self.links.append(attrs[key])
    def handle_endtag(self,tag):
        if tag=='template':self.in_template=False

class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)/'blog';cls.root.mkdir()
        for name in ('build.py','site.json'):shutil.copy2(ROOT/name,cls.root/name)
        for name in ('assets','content'):shutil.copytree(ROOT/name,cls.root/name)
        cls.build()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    @classmethod
    def build(cls, *, site_url=None):
        env=os.environ.copy()
        env.pop('BLOG_SITE_URL',None)
        if site_url is not None:
            env['BLOG_SITE_URL']=site_url
        return subprocess.run([sys.executable,'build.py'],cwd=cls.root,env=env,capture_output=True,text=True,encoding='utf-8',check=True)
    def test_build_site_url_and_stable_rss_identity(self):
        docs=self.root/'docs'
        original={p.relative_to(docs):p.read_bytes() for p in docs.rglob('*') if p.is_file()}
        settings=(self.root/'site.json').read_bytes()
        default_origin=json.loads(settings)['url'].rstrip('/')
        mirror_origin='https://4444hao.home64.de'
        default_feed=ET.fromstring(original[Path('feed.xml')]).find('channel')
        try:
            self.build(site_url=mirror_origin+'/')
            mirrored={p.relative_to(docs):p.read_bytes() for p in docs.rglob('*') if p.is_file()}
            self.assertEqual(original.keys(),mirrored.keys())
            for path,body in original.items():
                if path==Path('feed.xml'):
                    continue
                with self.subTest(path=str(path)):
                    self.assertEqual(mirrored[path],body.replace(default_origin.encode(),mirror_origin.encode()))
            mirror_feed=ET.fromstring(mirrored[Path('feed.xml')]).find('channel')
            self.assertEqual(mirror_feed.findtext('link'),mirror_origin+'/')
            self.assertEqual(len(default_feed.findall('item')),len(mirror_feed.findall('item')))
            for old,new in zip(default_feed.findall('item'),mirror_feed.findall('item')):
                self.assertEqual(new.findtext('link'),old.findtext('link').replace(default_origin,mirror_origin,1))
                for field in ('guid','title','description','pubDate'):
                    self.assertEqual(new.findtext(field),old.findtext(field))
                self.assertEqual(new.find('guid').get('isPermaLink'),'false')
            self.assertEqual((self.root/'site.json').read_bytes(),settings)
        finally:
            self.build()
        self.assertEqual(self.hash_output(),{str(p):hashlib.sha256(body).hexdigest() for p,body in original.items()})
    def test_invalid_site_url_preserves_output(self):
        snapshot=self.hash_output()
        for site_url in ('','ftp://example.com','//example.com','https://example.com/blog',
                         'https://example.com/?q=1','https://example.com/#records',
                         'https://user:password@example.com','https://example.com/ bad',
                         'https://example.com:invalid'):
            with self.subTest(site_url=site_url):
                with self.assertRaises(subprocess.CalledProcessError):
                    self.build(site_url=site_url)
                self.assertEqual(self.hash_output(),snapshot)
    def test_links_drafts_and_graph(self):
        notes=json.loads((self.root/'content/index.json').read_text(encoding='utf-8'))
        visible=[n for n in notes if not n['draft']]
        self.assertEqual(len(notes),len(list((self.root/'content').glob('*.md'))))
        expected=Counter(t for n in visible for t in n['tags'])
        expected_links=Counter(p for n in visible for p in combinations(sorted(n['tags']),2))
        graph=json.loads((self.root/'docs/assets/graph-data.json').read_text(encoding='utf-8'))
        self.assertEqual({n['tag']:n['count'] for n in graph['nodes']},dict(expected))
        self.assertEqual({(e['source'],e['target']):e['weight'] for e in graph['links']},dict(expected_links))
        parsed={}
        for file in (self.root/'docs').rglob('*.html'):
            parser=Links();parser.feed(file.read_text(encoding='utf-8'));parsed[file.resolve()]=parser
        for file,parser in parsed.items():
            for link in parser.links:
                url=urlsplit(link)
                if url.scheme or url.netloc:continue
                target=self.root/'docs'/unquote(url.path).lstrip('/') if url.path.startswith('/') else file.parent/unquote(url.path)
                if not url.path:target=file
                if target.is_dir():target=target/'index.html'
                self.assertTrue(target.exists(),(file,link))
                if url.fragment and target.suffix=='.html':self.assertIn(unquote(url.fragment),parsed[target.resolve()].ids,(file,link))
        for n in notes:self.assertEqual((self.root/'docs/essays'/n['slug']).exists(),not n['draft'])
        before=self.hash_output();self.build();self.assertEqual(before,self.hash_output())
    def test_diagrams_removed_from_public_note(self):
        source=(self.root/'content/note-1f486d44a9ee.md').read_text(encoding='utf-8')
        page=(self.root/'docs/essays/note-1f486d44a9ee/index.html').read_text(encoding='utf-8')
        self.assertNotIn('```mermaid',source)
        self.assertNotIn('mermaid-figure',page)
        self.assertFalse((self.root/'docs/assets/diagrams').exists())
    def test_existing_markdown_comparison_table_and_anchor(self):
        page=(self.root/'docs/essays/note-3bb820cc2c7a/index.html').read_text(encoding='utf-8')
        self.assertIn('id="一方法论的完整定义"',page)
        self.assertIn('href="#一方法论的完整定义"',page)
        self.assertRegex(page,r'<th scope="col"></th>\s*<th scope="col">延后学习</th>\s*<th scope="col">忽略不学</th>')
        self.assertNotIn('|--|---------|---------|',page)
    def test_markdown_keeps_notebook_rendering_rules(self):
        from build import markdown

        source = """# 中文标题

第一行
第二行带 ~~删除线~~。

1. 外层
   - 内层

> 引用 **加粗**

| 甲 | 乙 |
| :- | -: |
| A\\|B | 2 |

~~~text
| 不解析 | 表格 |
| -- | -- |
~~~

<div>原始 HTML</div>
"""
        rendered=markdown(source)
        self.assertIn('<h2 id="中文标题">中文标题</h2>',rendered)
        self.assertIn('第一行<br>\n第二行带 <s>删除线</s>。',rendered)
        self.assertRegex(rendered,r'<ol>\s*<li>外层\s*<ul>\s*<li>内层</li>')
        self.assertIn('<blockquote>\n<p>引用 <strong>加粗</strong></p>',rendered)
        self.assertEqual(rendered.count('<table>'),1)
        self.assertIn('role="region" aria-label="文章表格" tabindex="0"',rendered)
        self.assertIn('<td class="table-align-left">A|B</td>',rendered)
        self.assertIn('<td class="table-align-right">2</td>',rendered)
        self.assertIn('class="language-text">| 不解析 | 表格 |',rendered)
        self.assertIn('&lt;div&gt;原始 HTML&lt;/div&gt;',rendered)
    def test_rss_tracks_updated_public_notes(self):
        feed=self.root/'docs/feed.xml'
        channel=ET.parse(feed).getroot().find('channel')
        self.assertEqual(channel.findtext('title'),'走心旁白')
        self.assertEqual(channel.findtext('language'),'zh-CN')
        original=channel.findall('item')
        self.assertEqual(len(original),20)
        self.assertEqual(len({item.findtext('guid') for item in original}),len(original))
        for item in original:
            self.assertEqual(item.findtext('guid'),item.findtext('link'))
            self.assertTrue(item.findtext('description'))
            self.assertTrue(item.findtext('pubDate'))
            self.assertTrue((self.root/'docs'/urlsplit(item.findtext('link')).path.lstrip('/')/'index.html').exists())
        home=(self.root/'docs/index.html').read_text(encoding='utf-8')
        self.assertIn('rel="alternate" type="application/rss+xml"',home)
        self.assertIn('href="/feed.xml"',home)

        file=self.root/'content/test-rss-note.md'
        data={'title':'风 & 树','category':'短记','tags':['自然 & 风'],
              'summary':'一段 <安静> 的记录。','updated':'2099-01-01 12:00',
              'draft':False}
        def write():file.write_text('---\n'+yaml.safe_dump(data,allow_unicode=True,sort_keys=False)+'---\n\n新的正文。\n',encoding='utf-8')
        try:
            write();self.build()
            channel=ET.parse(feed).getroot().find('channel')
            item=channel.find('item')
            self.assertEqual(item.findtext('title'),'风 & 树')
            self.assertEqual(item.findtext('description'),'一段 <安静> 的记录。')
            self.assertEqual(item.findtext('category'),'短记')
            self.assertEqual(item.findall('category')[1].text,'自然 & 风')
            self.assertEqual(parsedate_to_datetime(item.findtext('pubDate')).isoformat(),'2099-01-01T12:00:00+08:00')
            stable_guid=item.findtext('guid')
            data['published']=date(2000,1,1);write();self.build()
            item=ET.parse(feed).getroot().find('channel/item')
            self.assertEqual(item.findtext('guid'),stable_guid)
            self.assertEqual(parsedate_to_datetime(item.findtext('pubDate')).isoformat(),'2099-01-01T12:00:00+08:00')
            data['updated']='2099-01-03 08:00';write();self.build()
            item=ET.parse(feed).getroot().find('channel/item')
            self.assertEqual(item.findtext('guid'),stable_guid)
            self.assertEqual(parsedate_to_datetime(item.findtext('pubDate')).isoformat(),'2099-01-03T08:00:00+08:00')
            data['draft']=True;write();self.build()
            self.assertNotIn('test-rss-note',feed.read_text(encoding='utf-8'))
            snapshot=self.hash_output()
            data['draft']=False;data['updated']='not-a-date';write()
            with self.assertRaises(subprocess.CalledProcessError):self.build()
            self.assertEqual(snapshot,self.hash_output())
        finally:
            file.unlink(missing_ok=True);self.build()
    def test_static_pagination_and_section_contents(self):
        notes=json.loads((self.root/'content/index.json').read_text(encoding='utf-8'))
        visible=sorted([n for n in notes if not n['draft']],key=lambda n:n['updatedAt'],reverse=True)
        bases={'/all/':None,'/essays/':'随笔','/notes/':'短记','/excerpts/':'摘录','/collections/':'专题整理'}
        for base,category in bases.items():
            subset=[n for n in visible if category is None or n['category']==category]
            pages=max(1,(len(subset)+9)//10);seen=[]
            for number in range(1,pages+1):
                path=base if number==1 else f'{base}page/{number}/'
                markup=(self.root/'docs'/path.lstrip('/')/'index.html').read_text(encoding='utf-8')
                parsed=Links();parsed.feed(markup)
                self.assertEqual(len(parsed.entries),len(subset[(number-1)*10:number*10]))
                self.assertLessEqual(len(parsed.entries),10)
                if parsed.entries:
                    self.assertIn('/"><h2>',markup)
                    self.assertNotIn('/"><h3>',markup)
                if category:
                    self.assertNotIn('home-title',parsed.ids)
                    self.assertTrue(all(e['data-category']==category for e in parsed.entries))
                self.assertIn('tag-graph',parsed.ids)
                self.assertIn('<details class="sidebar-explorer">',markup)
                seen.extend(e['data-category'] for e in parsed.entries)
            self.assertEqual(len(seen),len(subset))
        home=(self.root/'docs/index.html').read_text(encoding='utf-8')
        parsed=Links();parsed.feed(home)
        self.assertEqual([e['data-slug'] for e in parsed.entries],[n['slug'] for n in visible[:6]])
        self.assertEqual(len(parsed.entries),min(6,len(visible)))
        self.assertIn('最近笔记',home)
        self.assertIn('/"><h3>',home)
        self.assertIn('/all/#records',parsed.links)
        self.assertNotIn('pagination',parsed.ids)
        self.assertIn('tag-graph',parsed.ids)
        self.assertLess(home.index('class="sidebar-links"'),home.index('id="tag-graph"'))
        self.assertNotIn('class="sidebar-explorer"',home)
        self.assertIn('关于',home)
        article=(self.root/'docs/essays'/visible[0]['slug']/'index.html').read_text(encoding='utf-8')
        self.assertEqual(article.count('id="tag-graph"'),1)
        self.assertIn('<details class="sidebar-explorer">',article)
        self.assertLess(article.index('class="sidebar-links"'),article.index('class="sidebar-explorer"'))
        article_section=next(path for path,category in bases.items() if category==visible[0]['category'])
        self.assertIn(f'href="{article_section}" aria-current="location"',article)
    def test_recent_update_moves_old_note_and_displays_dates(self):
        file=self.root/'content/test-recent-update.md'
        data={'title':'修订旧笔记','category':'短记','tags':['测试更新'],'summary':'时间排序测试','updated':'2000-01-01','date':'1999-01-01','draft':False}
        def write():file.write_text('---\n'+yaml.safe_dump(data,allow_unicode=True,sort_keys=False)+'---\n\n旧文章的新补充。\n',encoding='utf-8')
        try:
            write();self.build()
            home=Links();home.feed((self.root/'docs/index.html').read_text(encoding='utf-8'))
            self.assertNotIn('test-recent-update',[e['data-slug'] for e in home.entries])
            data['updated']='2099-01-01';write();self.build()
            home=Links();home.feed((self.root/'docs/index.html').read_text(encoding='utf-8'))
            self.assertEqual(home.entries[0]['data-slug'],'test-recent-update')
            for path in ('all/index.html','notes/index.html'):
                parsed=Links();parsed.feed((self.root/'docs'/path).read_text(encoding='utf-8'))
                self.assertEqual(parsed.entries[0]['data-slug'],'test-recent-update')
            article=(self.root/'docs/essays/test-recent-update/index.html').read_text(encoding='utf-8')
            self.assertIn('写于 <time datetime="1999-01-01"',article)
            self.assertIn('更新于 <time datetime="2099-01-01"',article)
            # Same-day clock time wins over explicit order and date-only midnight.
            earlier=self.root/'content/test-earlier-update.md'
            earlier_data={**data,'title':'同日较早修订','updated':'2099-01-01 08:00','order':-999}
            earlier.write_text('---\n'+yaml.safe_dump(earlier_data,allow_unicode=True,sort_keys=False)+'---\n\n较早更新。\n',encoding='utf-8')
            data['updated']='2099-01-01 16:15';write();self.build()
            home=Links();home.feed((self.root/'docs/index.html').read_text(encoding='utf-8'))
            self.assertEqual([e['data-slug'] for e in home.entries[:2]],['test-recent-update','test-earlier-update'])
            self.assertIn('2099-01-01 16:15',(self.root/'docs/index.html').read_text(encoding='utf-8'))
            earlier.unlink()
            data.pop('date');write();self.build()
            article=(self.root/'docs/essays/test-recent-update/index.html').read_text(encoding='utf-8')
            self.assertNotIn('写于',article)
            self.assertIn('更新于',article)
        finally:
            file.unlink(missing_ok=True)
            (self.root/'content/test-earlier-update.md').unlink(missing_ok=True)
            self.build()

    def hash_output(self):
        return {str(p.relative_to(self.root/'docs')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.root/'docs').rglob('*') if p.is_file()}
    def test_new_tags_drafts_removal_and_bad_metadata(self):
        file=self.root/'content/test-new-topic.md'
        data={'title':'标签测试','category':'短记','tags':['新标签 & 风','自然','新标签 & 风'],'summary':'构建测试','updated':'2026-10-03','draft':False}
        def write():file.write_text('---\n'+yaml.safe_dump(data,allow_unicode=True,sort_keys=False)+'---\n\n测试正文。\n',encoding='utf-8')
        try:
            write();self.build()
            graph=json.loads((self.root/'docs/assets/graph-data.json').read_text(encoding='utf-8'))
            self.assertEqual(next(n['count'] for n in graph['nodes'] if n['tag']=='新标签 & 风'),1)
            self.assertTrue((self.root/'docs/essays/test-new-topic/index.html').exists())
            data['draft']=True;write();self.build()
            graph=json.loads((self.root/'docs/assets/graph-data.json').read_text(encoding='utf-8'))
            self.assertNotIn('新标签 & 风',{n['tag'] for n in graph['nodes']})
            self.assertFalse((self.root/'docs/essays/test-new-topic').exists())
            snapshot=self.hash_output();data['category']='不存在的分类';write()
            with self.assertRaises(subprocess.CalledProcessError):self.build()
            self.assertEqual(snapshot,self.hash_output())
        finally:
            file.unlink(missing_ok=True);self.build()

if __name__=='__main__':unittest.main()
