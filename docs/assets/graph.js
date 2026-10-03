/* Local SVG force layout; no external libraries, requests or continuous idle animation. */
(() => {
  'use strict';
  const svg = document.getElementById('tag-graph');
  if (!svg) return;
  const panel = document.getElementById('graph-panel');
  const list = document.getElementById('tag-list');
  const graphButton = document.getElementById('view-graph');
  const listButton = document.getElementById('view-list');
  const motionButton = document.getElementById('motion-toggle');
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const nodes = [...svg.querySelectorAll('.graph-node')].map(el => ({
    el, baseRadius:Number(el.dataset.radius), radius:0, x:0,y:0,vx:0,vy:0,dragging:false
  }));
  const edges = [...svg.querySelectorAll('.graph-edges line')].map(el => ({
    el, source:nodes[Number(el.dataset.source)], target:nodes[Number(el.dataset.target)], weight:Number(el.dataset.weight)
  }));
  let width=980, height=420, frame=0, ticks=0, paused=preference.matches;
  let selected=new URLSearchParams(location.search).get('tag') || '', hovered='', dragging=null;
  let active=true;
  document.querySelector('.graph-controls').hidden=false;
  panel.hidden=false; list.hidden=true;

  function paint() {
    for(const n of nodes) n.el.setAttribute('transform',`translate(${n.x.toFixed(2)} ${n.y.toFixed(2)})`);
    for(const e of edges) {
      e.el.setAttribute('x1',e.source.x); e.el.setAttribute('y1',e.source.y);
      e.el.setAttribute('x2',e.target.x); e.el.setAttribute('y2',e.target.y);
    }
  }
  function constrain(n) {
    const pad=n.radius+9;
    n.x=Math.max(pad,Math.min(width-pad,n.x)); n.y=Math.max(pad,Math.min(height-pad,n.y));
  }
  function physics() {
    for(const n of nodes) {
      if(n.dragging) continue;
      n.vx+=(width/2-n.x)*.00065; n.vy+=(height/2-n.y)*.00065;
    }
    for(let i=0;i<nodes.length;i++) for(let j=i+1;j<nodes.length;j++) {
      const a=nodes[i],b=nodes[j]; let dx=b.x-a.x,dy=b.y-a.y;
      let distance=Math.hypot(dx,dy);
      if(distance<.01) { dx=.5;dy=.4;distance=Math.hypot(dx,dy); }
      const push=Math.min(2.4,1100/(distance*distance));
      const ux=dx/distance,uy=dy/distance;
      if(!a.dragging) {a.vx-=ux*push;a.vy-=uy*push;}
      if(!b.dragging) {b.vx+=ux*push;b.vy+=uy*push;}
    }
    for(const e of edges) {
      const a=e.source,b=e.target,dx=b.x-a.x,dy=b.y-a.y,d=Math.max(1,Math.hypot(dx,dy));
      const ideal=a.radius+b.radius+56;
      const pull=(d-ideal)*.0007*Math.min(3,Math.sqrt(e.weight));
      if(!a.dragging){a.vx+=dx/d*pull;a.vy+=dy/d*pull;}
      if(!b.dragging){b.vx-=dx/d*pull;b.vy-=dy/d*pull;}
    }
    for(const n of nodes) {
      if(!n.dragging){ n.vx*=.83;n.vy*=.83;n.x+=n.vx;n.y+=n.vy;constrain(n); }
    }
    // Resolve collisions separately so close neighbors never hide each other.
    for(let pass=0;pass<4;pass++) for(let i=0;i<nodes.length;i++) for(let j=i+1;j<nodes.length;j++) {
      const a=nodes[i],b=nodes[j],dx=b.x-a.x,dy=b.y-a.y;
      const d=Math.max(.01,Math.hypot(dx,dy)),minimum=a.radius+b.radius+11;
      if(d<minimum) {
        const movement=(minimum-d)*.52,ux=dx/d,uy=dy/d;
        if(!a.dragging){a.x-=ux*movement;a.y-=uy*movement;constrain(a);}
        if(!b.dragging){b.x+=ux*movement;b.y+=uy*movement;constrain(b);}
      }
    }
  }
  function stop() {cancelAnimationFrame(frame);frame=0;}
  function run() {
    frame=0;
    if(paused||panel.hidden||document.hidden||!active) return;
    physics();paint();ticks--;
    if(ticks>0 || dragging) frame=requestAnimationFrame(run);
  }
  function start(count=160) {
    ticks=Math.max(ticks,count);
    if(!frame && !paused && !panel.hidden && !document.hidden && active) frame=requestAnimationFrame(run);
  }
  function resize() {
    if(panel.hidden) return;
    const oldWidth=width,oldHeight=height;
    width=Math.max(260,svg.clientWidth);
    height=width<480?430:400;
    svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
    const area=nodes.reduce((sum,n)=>sum+Math.PI*n.baseRadius**2,0);
    const scale=Math.min(1,Math.sqrt(width*height/(Math.max(1,area)*2.4)));
    nodes.forEach((n,i)=>{
      n.radius=n.baseRadius*scale;n.el.querySelector('circle').setAttribute('r',n.radius);
      if(!n.x) {
        const angle=i*2.399963229728653;
        const ring=Math.sqrt((i+.5)/Math.max(1,nodes.length));
        n.x=width/2+Math.cos(angle)*ring*(width/2-n.radius-30);
        n.y=height/2+Math.sin(angle)*ring*(height/2-n.radius-30);
      } else {n.x*=width/oldWidth;n.y*=height/oldHeight;}
      n.vx=n.vy=0;constrain(n);
    });
    // Prepare a collision-free arrangement before any visible animation starts.
    for(let i=0;i<120;i++) physics();
    paint();start();
  }
  function highlight() {
    const tag=hovered||selected;
    const center=nodes.find(n=>n.el.dataset.tag===tag);
    const related=new Set(center?[center]:[]);
    for(const e of edges) if(e.source===center || e.target===center) {
      related.add(e.source);related.add(e.target);
    }
    svg.classList.toggle('has-highlight',Boolean(center));
    for(const n of nodes) {
      n.el.classList.toggle('is-related',related.has(n));
      n.el.classList.toggle('is-active',n===center);
    }
    for(const e of edges) e.el.classList.toggle('is-active',e.source===center || e.target===center);
  }
  document.getElementById('records').addEventListener('tag-filter-change', e=>{selected=e.detail.tag;highlight();});
  function point(e) {
    const r=svg.getBoundingClientRect();
    return {x:(e.clientX-r.left)*width/r.width,y:(e.clientY-r.top)*height/r.height};
  }
  for(const n of nodes) {
    n.el.addEventListener('pointerenter',()=>{hovered=n.el.dataset.tag;highlight();});
    n.el.addEventListener('pointerleave',()=>{hovered='';highlight();});
    n.el.addEventListener('focus',()=>{hovered=n.el.dataset.tag;highlight();});
    n.el.addEventListener('blur',()=>{hovered='';highlight();});
    n.el.addEventListener('pointerdown',e=>{
      if(e.button!==0) return;
      const p=point(e);
      n.el.dataset.dragged='false';
      dragging={node:n,start:p,offset:{x:n.x-p.x,y:n.y-p.y},moved:false,id:e.pointerId};
      n.el.setPointerCapture(e.pointerId);
    });
    n.el.addEventListener('pointermove',e=>{
      if(!dragging || dragging.node!==n) return;
      const p=point(e);
      if(Math.hypot(p.x-dragging.start.x,p.y-dragging.start.y)>6) dragging.moved=true;
      if(!dragging.moved) return;
      n.dragging=true;n.el.dataset.dragged='true';
      n.x=p.x+dragging.offset.x;n.y=p.y+dragging.offset.y;n.vx=n.vy=0;constrain(n);
      physics();paint();start(80);
    });
    const release=()=>{
      if(!dragging || dragging.node!==n) return;
      n.dragging=false;
      dragging=null;start(80);
    };
    n.el.addEventListener('pointerup',release);
    n.el.addEventListener('pointercancel',()=>{n.el.dataset.dragged='false';release();});
    n.el.addEventListener('lostpointercapture',release);
  }
  function mode(graph) {
    if(dragging){dragging.node.dragging=false;dragging=null;}
    panel.hidden=!graph;list.hidden=graph;
    graphButton.setAttribute('aria-pressed',String(graph));listButton.setAttribute('aria-pressed',String(!graph));
    motionButton.hidden=!graph;
    if(graph){resize();}else stop();
  }
  graphButton.addEventListener('click',()=>mode(true));
  listButton.addEventListener('click',()=>mode(false));
  function motion() {
    motionButton.setAttribute('aria-pressed',String(paused));
    motionButton.textContent=paused?'启用动态':'暂停动态';
    if(paused)stop();else start();
  }
  motionButton.addEventListener('click',()=>{paused=!paused;motion();});
  preference.addEventListener('change',()=>{paused=preference.matches;motion();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else start(40);});
  new ResizeObserver(resize).observe(svg);
  new IntersectionObserver(entries=>{active=entries[0].isIntersecting;if(active)start(40);else stop();}).observe(panel);
  motion();resize();highlight();
})();
