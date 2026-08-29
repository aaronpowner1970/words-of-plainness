/* ═══════════════════════════════════════════════════════════════════
   APPROACHES TO BELIEF — /studies/approaches-to-belief/
   Slide engine, Contents menu, Study/Present toggle, two placement grids,
   reflection fields, quizzes, fork, export.
   All state lives in this browser only (localStorage key wop-atb-v1).
   No account, no server, no analytics on placement — do not add any.
   Markup: src/pages/studies/approaches-to-belief.njk · CSS: css/approaches.css
   ═══════════════════════════════════════════════════════════════════ */
(function(){
"use strict";
var app=document.getElementById('ab-app');
if(!app) return;
var slides=[].slice.call(app.querySelectorAll('.ab-slide'));
var i=0, KEY='wop-atb-v1';
var store={};
try{ store=JSON.parse(localStorage.getItem(KEY)||'{}'); }catch(e){ store={}; }
function save(){ try{ localStorage.setItem(KEY,JSON.stringify(store)); }catch(e){} }
function $(id){ return document.getElementById(id); }

/* ---------- contents menu ---------- */
var SECMETA={'0':{n:'✦',t:'Welcome'},'pre':{n:'•',t:'Where Do I Stand?'},
 '1':{n:'1',t:'How We Come to Know'},'2':{n:'2',t:'Reasons to be a Theist'},
 '3':{n:'3',t:'Reasons to be an Atheist'},'4':{n:'4',t:'Reasons to be Agnostic'},
 '5':{n:'5',t:'A Word for the Space Between'},'6':{n:'6',t:'The Third Axis'},
 '7':{n:'7',t:'Reason and Revelation'},'sum':{n:'✦',t:'Bringing It Together'}};
var ORDER=['0','pre','1','2','3','4','5','6','7','sum'];
var seen=(store._seen&&typeof store._seen==='object')?store._seen:{};

var tocBody=$('ab-tocBody'), items={};
ORDER.forEach(function(sec){
  var mine=[];
  slides.forEach(function(el,k){ if(el.dataset.sec===sec) mine.push({el:el,k:k}); });
  if(!mine.length) return;
  var m=SECMETA[sec]||{n:'',t:sec};
  var wrap=document.createElement('div'); wrap.className='ab-tsec'; wrap.dataset.sec=sec;
  var tt=document.createElement('div'); tt.className='ab-tt';
  tt.innerHTML='<span class="ab-n">'+m.n+'</span><span>'+m.t+'</span>';
  wrap.appendChild(tt);
  var list=document.createElement('div'); list.className='ab-tlist';
  mine.forEach(function(o){
    var b=document.createElement('button'); b.className='ab-ti'; b.type='button'; b.dataset.k=o.k;
    b.innerHTML='<span class="ab-dot"></span>'+(o.el.dataset.label||'');
    b.addEventListener('click',function(){ closeToc(); go(o.k); });
    list.appendChild(b); items[o.k]=b;
  });
  wrap.appendChild(list); tocBody.appendChild(wrap);
});

function paintToc(){
  var cur=slides[i].dataset.sec;
  Object.keys(items).forEach(function(key){
    var k=+key, b=items[key];
    b.classList.toggle('ab-cur',k===i);
    b.classList.toggle('ab-seen',!!seen[k]&&k!==i);
  });
  [].slice.call(tocBody.querySelectorAll('.ab-tsec')).forEach(function(w){
    w.classList.toggle('ab-cur',w.dataset.sec===cur);
  });
}
function openToc(){ document.body.classList.add('ab-tocopen'); paintToc();
  var c=items[i]; if(c) c.scrollIntoView({block:'center'}); }
function closeToc(){ document.body.classList.remove('ab-tocopen'); }
$('ab-tocBtn').addEventListener('click',function(){
  document.body.classList.contains('ab-tocopen')?closeToc():openToc(); });
$('ab-tocScrim').addEventListener('click',closeToc);

/* ---------- navigation ---------- */
function go(n){
  i=Math.max(0,Math.min(slides.length-1,n));
  slides.forEach(function(s,k){ s.classList.toggle('ab-on',k===i); });
  seen[i]=1; store._seen=seen; store._at=i;
  var cur=slides[i].dataset.sec, m=SECMETA[cur]||{t:cur};
  $('ab-where').innerHTML='<b>'+m.t+'</b>'+(slides[i].dataset.label||'');
  $('ab-progfill').style.width=
    (slides.length<2?100:(i/(slides.length-1))*100)+'%';
  $('ab-prev').disabled=(i===0);
  var nx=$('ab-next');
  nx.textContent=(i===slides.length-1)?'Done':'Next →';
  nx.disabled=(i===slides.length-1);
  paintToc();
  window.scrollTo({top:0,behavior:'auto'});
  save();
}
$('ab-prev').addEventListener('click',function(){go(i-1)});
[].slice.call(app.querySelectorAll('[data-goto]')).forEach(function(a){
  a.addEventListener('click',function(e){
    e.preventDefault();
    var sec=a.dataset.goto;
    for(var k=0;k<slides.length;k++){ if(slides[k].dataset.sec===sec){ closeToc(); go(k); return; } }
  });
});
$('ab-next').addEventListener('click',function(){go(i+1)});
document.addEventListener('keydown',function(e){
  var t=e.target.tagName;
  if(t==='TEXTAREA'||t==='INPUT'||t==='SELECT'||e.target.isContentEditable) return;
  if(e.ctrlKey||e.metaKey||e.altKey) return;
  if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){e.preventDefault();closeToc();go(i+1);}
  if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();closeToc();go(i-1);}
  if(e.key==='p'||e.key==='P'){setMode(!document.body.classList.contains('ab-present'));}
  if(e.key==='c'||e.key==='C'){document.body.classList.contains('ab-tocopen')?closeToc():openToc();}
  if(e.key==='Escape'){closeToc();}
});

/* ---------- mode (Study / Present) ---------- */
var bS=$('ab-mStudy'), bP=$('ab-mPresent');
function setMode(p){
  document.body.classList.toggle('ab-present',p);
  bP.classList.toggle('ab-on',p); bS.classList.toggle('ab-on',!p);
  bP.setAttribute('aria-pressed',p?'true':'false');
  bS.setAttribute('aria-pressed',p?'false':'true');
  store._mode=p?'present':'study'; save();
}
bS.onclick=function(){setMode(false)}; bP.onclick=function(){setMode(true)};

/* ---------- journal fields ---------- */
[].slice.call(app.querySelectorAll('[data-j]')).forEach(function(el){
  var k=el.dataset.j;
  if(store[k]!=null) el.value=store[k];
  el.addEventListener('input',function(){ store[k]=el.value; save(); });
});

/* ---------- quizzes ---------- */
[].slice.call(app.querySelectorAll('[data-quiz]')).forEach(function(box){
  var id=box.dataset.quiz, ans=box.dataset.answer;
  var fb=app.querySelector('[data-fb="'+id+'"]');
  box.addEventListener('click',function(e){
    var o=e.target.closest('.ab-opt'); if(!o) return;
    [].slice.call(box.querySelectorAll('.ab-opt')).forEach(function(x){
      x.classList.remove('ab-sel','ab-right','ab-wrong');
      if(x.dataset.k===ans) x.classList.add('ab-right');
    });
    if(o.dataset.k!==ans) o.classList.add('ab-wrong');
    fb.classList.add('ab-on');
    store['quiz-'+id]=o.dataset.k; save();
  });
  if(store['quiz-'+id]){
    var pre=box.querySelector('.ab-opt[data-k="'+store['quiz-'+id]+'"]');
    if(pre) pre.click();
  }
});

/* ---------- grids ---------- */
var DATA={
 at:{n:'Agnostic Theist',d:'You believe that deity exists. You do not claim to know it.',
     a:'You believe without claiming to know. There may be more knowing in that than you have given yourself credit for.'},
 gt:{n:'Gnostic Theist',d:'You believe that deity exists, and you claim to know it.',
     a:'You claim to know. So do I. The question worth sitting with is how much — and whether certainty about God requires certainty about everything attached to Him.'},
 aa:{n:'Agnostic Atheist',d:'You do not believe that deity exists. You do not claim to know that none exists.',
     a:'You decline to claim knowledge you do not have. That is a discipline, not a deficiency — and it may be closer to Section 5 than you expect.'},
 ga:{n:'Gnostic Atheist',d:'You do not believe that deity exists, and you claim to know that none exists.',
     a:'You claim knowledge of a universal negative. Applied evenly, would the standards you use elsewhere grant you that?'}
};
function quad(x,y){ return y<310?(x<310?'at':'gt'):(x<310?'aa':'ga'); }
function art(n){ return /^[AEIOU]/i.test(n)?'an':'a'; }

function wire(tag,onPlace){
  var svg=$('ab-grid'+tag);
  function mark(x,y){
    $('ab-'+tag+'-c1').setAttribute('cx',x);
    $('ab-'+tag+'-c1').setAttribute('cy',y);
    $('ab-'+tag+'-c2').setAttribute('cx',x);
    $('ab-'+tag+'-c2').setAttribute('cy',y);
    $('ab-'+tag+'-mk').classList.add('ab-on');
    svg.classList.add('ab-chosen');
    var k=quad(x,y);
    ['at','gt','aa','ga'].forEach(function(q){
      $('ab-'+tag+'-'+q).classList.toggle('ab-lit',q===k);
    });
    return k;
  }
  function place(ev){
    var pt=svg.createSVGPoint(), src=ev.touches?ev.touches[0]:ev;
    pt.x=src.clientX; pt.y=src.clientY;
    var l=pt.matrixTransform(svg.getScreenCTM().inverse());
    var x=Math.max(60,Math.min(560,l.x)), y=Math.max(60,Math.min(560,l.y));
    onPlace(mark(x,y),x,y);
  }
  svg.addEventListener('click',place);
  svg.addEventListener('touchstart',function(e){e.preventDefault();place(e);},{passive:false});
  return function(x,y){ // programmatic restore
    onPlace(mark(x,y),x,y,true);
  };
}

var restoreA=wire('A',function(k,x,y){
  var d=DATA[k];
  $('ab-nameA').textContent=d.n;
  $('ab-defA').textContent=d.d;
  $('ab-appA').textContent=d.a;
  $('ab-resA').classList.add('ab-on');
  $('ab-hintA').textContent='Click again to move. Nothing is recorded beyond this browser.';
  store.preQ=k; store.preX=x; store.preY=y; save();
});

var restoreB=wire('B',function(k,x,y){
  var d=DATA[k];
  $('ab-nameB').textContent=d.n;
  var msg;
  if(!store.preQ){ msg=d.d; }
  else if(store.preQ===k){
    msg='You began here and you have stayed here. That is a legitimate result — and after seven sections of honest pressure, staying put is itself a finding. The question is whether you hold it for the same reasons you did an hour ago.';
  } else {
    msg='You began as '+art(DATA[store.preQ].n)+' '+DATA[store.preQ].n+'. '+d.d+' Something moved. Movement was never the goal, but it is worth understanding — a position you arrived at is worth more than one you inherited.';
  }
  $('ab-moveB').textContent=msg;
  $('ab-resB').classList.add('ab-on');
  $('ab-hintB').textContent='Click again to adjust.';
  store.postQ=k; store.postX=x; store.postY=y; save();
  drawGhost();
});

function drawGhost(){
  if(store.preX==null) return;
  var g=$('ab-ghost');
  $('ab-gh1').setAttribute('cx',store.preX);
  $('ab-gh1').setAttribute('cy',store.preY);
  $('ab-ghlab').setAttribute('x',store.preX);
  $('ab-ghlab').setAttribute('y',store.preY-20);
  g.style.display='';
  if(store.postX!=null){
    var L=$('ab-movline');
    L.setAttribute('x1',store.preX); L.setAttribute('y1',store.preY);
    L.setAttribute('x2',store.postX); L.setAttribute('y2',store.postY);
    L.style.display='';
  }
}
/* ---------- clearing placements ----------
   Erase everything wiped the store but left both grids painted: markers, lit
   quadrants, result panels, the ghost and the movement line all survived until
   reload. resetGridUI() puts the SVGs back to their unplaced state; the global
   erase and the grid-scoped reset both call it. ---------- */
var HINT_A=$('ab-hintA').textContent, HINT_B=$('ab-hintB').textContent;
function clearGridUI(tag){
  var svg=$('ab-grid'+tag);
  $('ab-'+tag+'-c1').setAttribute('cx',310); $('ab-'+tag+'-c1').setAttribute('cy',310);
  $('ab-'+tag+'-c2').setAttribute('cx',310); $('ab-'+tag+'-c2').setAttribute('cy',310);
  $('ab-'+tag+'-mk').classList.remove('ab-on');
  svg.classList.remove('ab-chosen');
  ['at','gt','aa','ga'].forEach(function(q){ $('ab-'+tag+'-'+q).classList.remove('ab-lit'); });
  $('ab-res'+tag).classList.remove('ab-on');
}
function resetGridUI(){
  clearGridUI('A'); clearGridUI('B');
  $('ab-hintA').textContent=HINT_A; $('ab-hintB').textContent=HINT_B;
  $('ab-ghost').style.display='none';
  $('ab-movline').style.display='none';
}
$('ab-gridclr').onclick=function(){
  ['preQ','preX','preY','postQ','postX','postY'].forEach(function(k){ delete store[k]; });
  save(); resetGridUI();
  var f=$('ab-gridclrfb');
  f.textContent='Both placements cleared. Everything you wrote is untouched.';
  f.classList.add('ab-on');
};

if(store.preX!=null){ restoreA(store.preX,store.preY); drawGhost(); }
if(store.postX!=null){ restoreB(store.postX,store.postY); }

/* ---------- fork ---------- */
[].slice.call(app.querySelectorAll('.ab-forkcard')).forEach(function(c){
  c.onclick=function(){
    [].slice.call(app.querySelectorAll('.ab-forkcard')).forEach(function(x){x.classList.remove('ab-sel')});
    c.classList.add('ab-sel');
    var f=c.dataset.fork;
    $('ab-forkExperiment').style.display=(f==='experiment')?'':'none';
    $('ab-forkLong').style.display=(f==='long')?'':'none';
    store.fork=f; save();
  };
});
if(store.fork){ var fc=app.querySelector('.ab-forkcard[data-fork="'+store.fork+'"]'); if(fc) fc.click(); }

/* ---------- export ---------- */
var LABELS={'pre-why':'Why I hold my position','s1-trust':'The path I trust most','s1-question':'The question reason has not settled',
 's2-steel':'Strongest reason for theism','s2-obj':'Hardest objection to theism','s3-steel':'Strongest reason for atheism',
 's3-force':'The atheist argument with real force','s4-steel':'Strongest reason for agnosticism','s4-shift':'What shifted',
 's4-change':'What would change my mind','s5-recognize':'What I recognize in merognosticism','s6-zaxis':'My proposed third axis',
 's6-depth':'Where I use a good instrument at the wrong depth','s7-edge':'The question reason brought me to',
 's7-convenient':'On the "missing information" claim','sum-move':'What accounts for the movement',
 'goal-what':'My experiment','goal-start':'Start date','goal-review':'Evaluation date',
 'goal-criteria':'What I would accept as a result','goal-prayer':'How I would prepare, and what I would ask'};
function buildText(){
  var out='APPROACHES TO BELIEF — My Reflections\nWords of Plainness\n\n';
  if(store.preQ) out+='Where I began: '+DATA[store.preQ].n+'\n';
  if(store.postQ) out+='Where I ended: '+DATA[store.postQ].n+
    (store.preQ===store.postQ?'  (unchanged)':'  (moved)')+'\n';
  out+='\n';
  Object.keys(LABELS).forEach(function(k){
    if(store[k] && String(store[k]).trim()){
      out+='— '+LABELS[k]+'\n'+store[k]+'\n\n';
    }
  });
  out+='\nIf any man will do his will, he shall know of the doctrine. — John 7:17\n';
  return out;
}
$('ab-dl').onclick=function(){
  var b=new Blob([buildText()],{type:'text/plain;charset=utf-8'});
  var a=document.createElement('a');
  a.href=URL.createObjectURL(b); a.download='approaches-to-belief-reflections.txt';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
};
$('ab-pr').onclick=function(){ window.print(); };
$('ab-clr').onclick=function(){
  store={}; try{localStorage.removeItem(KEY);}catch(e){}
  [].slice.call(app.querySelectorAll('[data-j]')).forEach(function(el){el.value='';});
  resetGridUI();
  $('ab-gridclrfb').classList.remove('ab-on');
  var f=$('ab-clrfb');
  f.textContent='Erased. Nothing remains in this browser.'; f.classList.add('ab-on');
};

/* ---------- boot ---------- */
if(store._mode==='present') setMode(true);
go(typeof store._at==='number'?store._at:0);
})();
