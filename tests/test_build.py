"""Build validation uses an isolated copy, so it never touches real notes."""
import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from html.parser import HTMLParser
from itertools import combinations
from pathlib import Path
from urllib.parse import unquote, urlsplit
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
    def build(cls):
        return subprocess.run([sys.executable,'build.py'],cwd=cls.root,capture_output=True,text=True,encoding='utf-8',check=True)
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
    def test_static_pagination_and_section_contents(self):
        notes=json.loads((self.root/'content/index.json').read_text(encoding='utf-8'))
        visible=sorted([n for n in notes if not n['draft']],key=lambda n:n.get('date',''),reverse=True)
        bases={'/':None,'/essays/':'随笔','/notes/':'短记','/excerpts/':'摘录','/collections/':'专题整理'}
        for base,category in bases.items():
            subset=[n for n in visible if category is None or n['category']==category]
            pages=max(1,(len(subset)+9)//10);seen=[]
            for number in range(1,pages+1):
                path=base if number==1 else f'{base}page/{number}/'
                markup=(self.root/'docs'/path.lstrip('/')/'index.html').read_text(encoding='utf-8')
                parsed=Links();parsed.feed(markup)
                self.assertEqual(len(parsed.entries),len(subset[(number-1)*10:number*10]))
                self.assertLessEqual(len(parsed.entries),10)
                if category:
                    self.assertNotIn('tag-graph',parsed.ids)
                    self.assertNotIn('home-title',parsed.ids)
                    self.assertTrue(all(e['data-category']==category for e in parsed.entries))
                else:self.assertIn('tag-graph',parsed.ids)
                seen.extend(e['data-category'] for e in parsed.entries)
            self.assertEqual(len(seen),len(subset))
        self.assertIn('关于',(self.root/'docs/index.html').read_text(encoding='utf-8'))
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
