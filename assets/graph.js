/* Local SVG force layout; no external libraries, requests or continuous idle animation. */
(() => {
  'use strict';
  const svg = document.getElementById('tag-graph');
  if (!svg) return;
  const panel = document.getElementById('graph-panel');
  const list = document.getElementById('tag-list');
  const graphButton = document.getElementById('view-graph');
  const listButton = document.getElementById('view-list');
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  const nodes = [...svg.querySelectorAll('.graph-node')].map(el => ({
    el, baseRadius:Number(el.dataset.radius), radius:0, x:0,y:0,vx:0,vy:0,
    anchorX:0,anchorY:0,dragging:false,placed:false
  }));
  const edges = [...svg.querySelectorAll('.graph-edges line')].map(el => ({
    el, source:nodes[Number(el.dataset.source)], target:nodes[Number(el.dataset.target)], weight:Number(el.dataset.weight)
  }));
  let width=980, height=420, frame=0, ticks=0, paused=preference.matches, layoutWide=false;
  let selected=new URLSearchParams(location.search).get('tag') || '', hovered='', dragging=null;
  let active=true;
  document.querySelector('.graph-controls').hidden=false;

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
      if(layoutWide) {
        const anchorStrength=n.placed ? .06 : .012;
        n.vx+=(n.anchorX-n.x)*anchorStrength; n.vy+=(n.anchorY-n.y)*anchorStrength;
      } else {
        n.vx+=(width/2-n.x)*.00065; n.vy+=(height/2-n.y)*.00065;
      }
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
      const touchingDrag=a.dragging || b.dragging;
      const strength=layoutWide ? (touchingDrag ? .0012 : .00013) : .0007;
      const pull=(d-ideal)*strength*Math.min(3,Math.sqrt(e.weight));
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
  function start(count=60) {
    ticks=Math.max(ticks,count);
    if(!frame && !paused && !panel.hidden && !document.hidden && active) frame=requestAnimationFrame(run);
  }
  function resize() {
    if(panel.hidden) return;
    const oldWidth=width,oldHeight=height,wasWide=layoutWide;
    width=Math.max(260,svg.clientWidth);
    layoutWide=width>=760;
    svg.classList.toggle('is-wide',layoutWide);
    svg.closest('.topics').classList.toggle('wide-graph',layoutWide);
    height=layoutWide?Math.min(380,180+Math.max(0,nodes.length-14)*10):(width<480?430:400);
    if(svg.style.height!==`${height}px`) svg.style.height=`${height}px`;
    svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
    const area=nodes.reduce((sum,n)=>sum+Math.PI*n.baseRadius**2,0);
    const scale=layoutWide ? .58 : Math.min(1,Math.sqrt(width*height/(Math.max(1,area)*2.4)));
    // On a wide page, the three most-used topics form loose centers. Other
    // topics sit near the center with which they share the most notes.
    const major=nodes.slice(0,Math.min(3,nodes.length));
    const groups=major.map(()=>[]);
    if(layoutWide) for(let i=major.length;i<nodes.length;i++) {
      const n=nodes[i];
      let choice=0,score=-1;
      major.forEach((m,j)=>{
        const edge=edges.find(e=>(e.source===n&&e.target===m)||(e.target===n&&e.source===m));
        const candidate=(edge?edge.weight:0)*100-groups[j].length;
        if(candidate>score){score=candidate;choice=j;}
      });
      groups[choice].push(n);
    }
    const spread=Math.min(108,width/(major.length*4.2));
    major.forEach((n,j)=>{
      n.anchorX=width*(j+.5)/major.length;
      n.anchorY=height*(.52+Math.sin((j+1)*1.7)*.05);
      groups[j].forEach((child,k)=>{
        const side=k%2===0?-1:1;
        const rank=Math.floor(k/2);
        child.anchorX=n.anchorX+side*spread*(.85+rank*.22);
        child.anchorY=n.anchorY+(k%4<2?-1:1)*(42+rank*5)+Math.sin((k+1)*(j+2)*1.7)*8;
      });
    });
    nodes.forEach((n,i)=>{
      n.radius=layoutWide?Math.max(n.baseRadius*scale,10+Math.min(4,n.el.dataset.tag.length)*6):n.baseRadius*scale;
      n.el.querySelector('circle').setAttribute('r',n.radius);
      if(layoutWide && (!n.x || !wasWide)) {
        n.x=n.anchorX;n.y=n.anchorY;
      } else if(!n.x || (wasWide && !layoutWide)) {
        const angle=i*2.399963229728653;
        const ring=Math.sqrt((i+.5)/Math.max(1,nodes.length));
        n.x=width/2+Math.cos(angle)*ring*(width/2-n.radius-30);
        n.y=height/2+Math.sin(angle)*ring*(height/2-n.radius-30);
      } else {n.x*=width/oldWidth;n.y*=height/oldHeight;}
      n.vx=n.vy=0;constrain(n);
      if(n.placed && layoutWide && wasWide){n.anchorX=n.x;n.anchorY=n.y;}
      if(!layoutWide || !wasWide) n.placed=false;
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
      // Keep a deliberately moved desktop topic near its release point.
      // Its linked topics settle briefly, while idle diagrams stay still.
      if(dragging.moved && layoutWide){n.anchorX=n.x;n.anchorY=n.y;n.placed=true;}
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
    if(graph){resize();}else stop();
  }
  graphButton.addEventListener('click',()=>mode(true));
  listButton.addEventListener('click',()=>mode(false));
  preference.addEventListener('change',()=>{paused=preference.matches;if(paused)stop();else start();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else start(40);});
  new ResizeObserver(resize).observe(svg);
  new IntersectionObserver(entries=>{active=entries[0].isIntersecting;if(active)start(40);else stop();}).observe(panel);
  mode(true);highlight();
})();
