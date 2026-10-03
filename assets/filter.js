/* Keep pagination and homepage tag state in the URL; the static pages work without JS. */
(() => {
  'use strict';
  const records=document.getElementById('records');
  const catalog=document.getElementById('article-catalog');
  if(!records || !catalog) return;
  const home=records.dataset.kind==='home';
  const base=records.dataset.base;
  const size=Number(records.dataset.pageSize);
  const entries=[...catalog.content.querySelectorAll('.essay-entry')];
  const metadata=entries.map(el=>({el,category:el.dataset.category,tags:JSON.parse(el.dataset.tags)}));
  const knownTags=new Set(metadata.flatMap(n=>n.tags));
  const knownCategories=new Set(metadata.map(n=>n.category));
  const tagButtons=[...document.querySelectorAll('[data-tag]')];
  const list=records.querySelector('.essay-list');
  const pager=document.getElementById('pagination');
  const heading=document.getElementById('records-title');
  const originalTitle=heading.textContent;
  const toolbar=document.getElementById('home-filter-status');
  const clear=document.getElementById('clear-filters');
  const remove=document.getElementById('remove-tag');
  let tag='',category='',number=1;
  function positive(value) {return /^\d+$/.test(value || '') && Number.isSafeInteger(Number(value)) && Number(value)>0 ? Number(value) : 1;}
  function readState() {
    const params=new URLSearchParams(location.search);
    tag=home && knownTags.has(params.get('tag')) ? params.get('tag') : '';
    category=home && knownCategories.has(params.get('category')) ? params.get('category') : '';
    const remainder=location.pathname.startsWith(base)?location.pathname.slice(base.length):'';
    const match=/^page\/(\d+)\/$/.exec(remainder);
    number=params.has('page') ? positive(params.get('page')) : (match?positive(match[1]):1);
  }
  function pageURL(target) {
    let path=target===1 ? base : `${base}page/${target}/`;
    const params=new URLSearchParams();
    if(tag || category) {
      path='/';
      if(tag)params.set('tag',tag);
      if(category)params.set('category',category);
      if(target!==1)params.set('page',String(target));
    }
    return path+(params.size?`?${params}`:'')+'#records';
  }
  function step(target,label,disabled,kind='',rel='') {
    const el=document.createElement(disabled?'span':'a');
    el.className=kind;el.textContent=label;
    if(disabled)el.setAttribute('aria-disabled','true');
    else {el.href=pageURL(target);el.dataset.page=String(target);if(rel)el.rel=rel;}
    return el;
  }
  function renderPager(pages) {
    pager.replaceChildren();pager.hidden=pages<=1;
    pager.append(step(number-1,'上一页',number===1,'pager-step','prev'));
    const numbers=document.createElement('div');numbers.className='page-numbers';
    const chosen=new Set([1,pages]);
    for(let i=Math.max(1,number-2);i<=Math.min(pages,number+2);i++)chosen.add(i);
    let last=0;
    for(const i of [...chosen].sort((a,b)=>a-b)) {
      if(last && i-last>1){const gap=document.createElement('span');gap.textContent='…';gap.className='page-gap';gap.setAttribute('aria-hidden','true');numbers.append(gap);}
      const link=step(i,String(i),i===number,'page-number');
      if(i===number){link.removeAttribute('aria-disabled');link.setAttribute('aria-current','page');}
      numbers.append(link);last=i;
    }
    const indicator=document.createElement('span');indicator.className='page-indicator';indicator.textContent=`第 ${number} / ${pages} 页`;
    pager.append(numbers,indicator,step(number+1,'下一页',number===pages,'pager-step','next'));
  }
  function render(historyMode='',scroll=false) {
    const matches=metadata.filter(n=>(!tag || n.tags.includes(tag)) && (!category || n.category===category));
    const total=matches.length,pages=Math.max(1,Math.ceil(total/size));
    number=Math.min(pages,Math.max(1,number));
    list.replaceChildren(...matches.slice((number-1)*size,number*size).map(n=>n.el.cloneNode(true)));
    document.getElementById('list-summary').textContent=`共 ${total} 篇 · 第 ${number} / ${pages} 页`;
    heading.textContent=home && (tag || category) ? '筛选后的笔记' : originalTitle;
    tagButtons.forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.tag===tag)));
    if(toolbar) {
      toolbar.hidden=!(tag || category);
      document.getElementById('filter-description').textContent=[category,tag?`标签：${tag}`:''].filter(Boolean).join(' · ');
      document.getElementById('result-count').textContent=`${total} 篇`;
      remove.hidden=!tag;
    }
    document.getElementById('empty-results').hidden=total!==0;
    renderPager(pages);
    if(historyMode) {
      const next=pageURL(number);
      const current=location.pathname+location.search+location.hash;
      if(historyMode==='push' && next!==current)history.pushState(null,'',next);
      else if(historyMode==='replace' && next!==current)history.replaceState(null,'',next);
    }
    records.dispatchEvent(new CustomEvent('tag-filter-change',{detail:{tag,category}}));
    if(scroll){heading.focus({preventScroll:true});records.scrollIntoView({block:'start',behavior:'instant'});}
  }
  pager.addEventListener('click',e=>{
    const link=e.target.closest('a[data-page]');
    if(!link || e.button!==0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)return;
    e.preventDefault();number=positive(link.dataset.page);render('push',true);
  });
  tagButtons.forEach(el=>{
    el.addEventListener('click',e=>{
      if(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)return;
      e.preventDefault();
      if(el.dataset.dragged==='true'){el.dataset.dragged='false';return;}
      tag=tag===el.dataset.tag?'':el.dataset.tag;number=1;render('push');
    });
    el.addEventListener('keydown',e=>{
      if((el.tagName.toLowerCase()==='g' && e.key==='Enter') || e.key===' '){
        e.preventDefault();el.dataset.dragged='false';el.dispatchEvent(new MouseEvent('click',{bubbles:true}));
      }
    });
  });
  function reset(){tag='';category='';number=1;render('push');}
  if(clear)clear.addEventListener('click',()=>{reset();heading.focus({preventScroll:true});});
  if(remove)remove.addEventListener('click',()=>{tag='';number=1;render('push');heading.focus({preventScroll:true});});
  document.getElementById('empty-clear').addEventListener('click',()=>{reset();heading.focus({preventScroll:true});});
  window.addEventListener('popstate',()=>{readState();render('',true);});
  readState();render();
  // Normalize invalid page numbers without moving ordinary first visits down to the list.
  const params=new URLSearchParams(location.search);
  if(params.has('page') && params.get('page')!==String(number))render('replace');
})();
