"""
Builds Aaron's lyric review packet: ONE self-contained offline HTML file.

Reads tools/reports/lyric_audit_<date>.json (from wop_audit_sung.py) and
writes C:\\Users\\aaron\\Documents\\wop-scratch\\LyricReview\\WoP_Lyric_Review_<date>.html.

Audio streams from https://media.wordsofplainness.org/web/<file>; nothing else
is fetched (no external scripts or fonts). Work autosaves in localStorage and
"Export decisions" downloads WoP_Lyric_Decisions_<date>.json.

This tool never edits any lyric sheet or site file: proposals are drafts for
the author, labelled "draft - not confirmed".

Usage: python tools/build_lyric_review.py [--audit tools/reports/lyric_audit_YYYYMMDD.json]
"""
import argparse
import datetime
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = Path(r"C:\Users\aaron\Documents\wop-scratch\LyricReview")
MEDIA = "https://media.wordsofplainness.org/web/"


def style_line(raw):
    """Heard text cased and punctuated like the sheet (a draft, nothing more)."""
    t = re.sub(r"\s+", " ", raw).strip()
    if not t:
        return t
    t = re.sub(r"\bi\b", "I", t)
    t = re.sub(r"\bi'(m|ve|ll|d)\b", lambda m: "I'" + m.group(1), t)
    t = t[0].upper() + t[1:]
    t = re.sub(r"[.,;:!?]+$", "", t) + ","
    return t


def build(audit_path):
    audit = json.loads(Path(audit_path).read_text(encoding="utf-8"))
    date = audit["date"]
    items = []
    for r in audit["arrangements"]:
        findings = []
        for u in r["unsheeted"]:
            findings.append(dict(kind="UNSHEETED", t=u["start"], sheet=u["sheet_near"] or "(nothing nearby on the sheet)",
                                 sheet_note=f"nearest sheet text, around line {u['near_line']}",
                                 heard=u["heard"], proposal=style_line(u["heard"]),
                                 what="The recording sings words that are not on the sheet here."))
        for u in r["unsung"]:
            findings.append(dict(kind="UNSUNG", t=u["expected"], sheet=u["text"], sheet_note=f"sheet line {u['line']}",
                                 heard="(no matching words heard)", proposal=u["text"],
                                 what="The recording may skip this sheet line."))
        for s in r["substitutions"]:
            if s["noise"]:
                continue
            findings.append(dict(kind="SUBSTITUTION", t=s["t"], sheet=s["sheet"], sheet_note=f"sheet line {s['line']}",
                                 heard=s["heard"], proposal=style_line(s["heard"]) if s["heard"] else s["sheet"],
                                 what=f"Sheet words '{s['sheet_words']}' vs heard words (raw diff, similarity {s['ratio']})."))
        findings.sort(key=lambda f: (f["t"] is None, f["t"] or 0))
        items.append(dict(stem=r["stem"], file=r["file"], title=r["title"] or r["stem"], label=r["label"] or "",
                          status=r["proposed_status"], direct=r["direct_pct"], model=r["model"],
                          findings=findings, sheet=r["sheet"]))
    return date, items


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WoP Lyric Review __DATE__</title>
<style>
body{font:20px/1.5 Georgia,'Times New Roman',serif;margin:0;background:#faf7f2;color:#222}
main{max-width:1000px;margin:0 auto;padding:16px 20px 80px}
h1{font-size:1.6rem;margin:.4em 0}
.top{background:#fff;border:2px solid #b8893a;border-radius:8px;padding:12px 16px;margin-bottom:18px}
.top code{background:#f1ead9;padding:2px 6px;border-radius:4px;font-size:.85em}
button{font:inherit;font-size:.9rem;padding:8px 14px;border-radius:6px;border:1px solid #888;background:#fff;cursor:pointer}
button:hover{background:#f1ead9}
button.on{background:#2f6b3a;color:#fff;border-color:#2f6b3a}
button.on.hold{background:#9a6a00;border-color:#9a6a00}
button.big{background:#7a1f2b;color:#fff;border-color:#7a1f2b;font-size:1rem}
section.arr{background:#fff;border:1px solid #ccc;border-radius:8px;margin:16px 0;padding:14px 18px}
section.arr h2{margin:0 0 4px;font-size:1.25rem}
.meta{color:#555;font-size:.8rem;word-break:break-all}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.8rem;color:#fff;margin-left:8px;vertical-align:middle}
.hold-candidate{background:#a02020}.review{background:#b8860b}.clean{background:#2f6b3a}
audio{width:100%;margin:8px 0}
.finding{border-left:5px solid #b8893a;background:#fbf7ee;margin:12px 0;padding:8px 12px;border-radius:0 6px 6px 0}
.finding.UNSUNG{border-color:#4a6fa5}.finding.SUBSTITUTION{border-color:#7a4a9a}
.kind{font-weight:bold;font-size:.8rem;letter-spacing:.05em}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:6px 0}
@media (max-width:760px){.cols{grid-template-columns:1fr}}
.col h4{margin:0;font-size:.75rem;color:#666;text-transform:uppercase}
.col div{background:#fff;border:1px solid #ddd;padding:6px 8px;border-radius:4px;font-size:.95rem}
textarea,input[type=text]{font:inherit;font-size:.95rem;width:100%;box-sizing:border-box;padding:6px 8px;border:1px solid #999;border-radius:4px}
textarea{min-height:2.6em}
.draft{font-size:.75rem;color:#a02020;font-weight:bold}
.sheet{margin-top:12px}
.sheet .ln{display:flex;gap:6px;align-items:center;margin:3px 0}
.sheet .n{width:2.2em;text-align:right;color:#888;font-size:.8rem}
.sheet .ln button{padding:2px 8px}
.decide{margin-top:12px;display:flex;gap:10px;flex-wrap:wrap}
details.clean-box>summary{font-size:1.2rem;cursor:pointer;margin:20px 0 6px}
.saved{color:#2f6b3a;font-size:.8rem}
</style></head><body><main>
<h1>WoP lyric review - __DATE__</h1>
<div class="top">
<p><b>How to use.</b> Each section is one recording. Press <b>Play from</b> on a finding to hear it (it starts 2 seconds early). Edit the proposed text if useful, fix the full sheet at the bottom if the audit missed something, then press one of the three buttons. Your work saves itself in this browser; closing the tab loses nothing.</p>
<p><b>When finished, press Export decisions</b> and save the file in <code>C:\Users\aaron\Documents\wop-scratch\LyricReview\</code></p>
<p><button class="big" id="export">Export decisions</button> <span id="count"></span> <span class="saved" id="saved"></span></p>
<p class="meta">Proposals are drafts made from speech recognition: <b>draft - not confirmed</b>. Nothing here changes the website.</p>
</div>
<div id="root"></div>
</main>
<script>
var DATA = __DATA__;
var DATE = "__DATE__";
var KEY = "wop-lyric-review-" + DATE;
var MEDIA = "__MEDIA__";
var state = {};
function load(){ try{ state = JSON.parse(localStorage.getItem(KEY)||"{}"); }catch(e){ state={}; } }
function save(){ try{ localStorage.setItem(KEY, JSON.stringify(state)); var s=document.getElementById('saved'); s.textContent='saved '+new Date().toLocaleTimeString(); }catch(e){ document.getElementById('saved').textContent='(could not autosave in this browser)'; } updateCount(); }
function st(stem){ if(!state[stem]) state[stem]={decision:null,lines:null,proposals:{}}; return state[stem]; }
function el(tag, attrs, kids){ var e=document.createElement(tag); for(var k in (attrs||{})){ if(k==='text') e.textContent=attrs[k]; else if(k==='cls') e.className=attrs[k]; else e.setAttribute(k,attrs[k]); } (kids||[]).forEach(function(c){ e.appendChild(c); }); return e; }
function mmss(t){ t=Math.max(0,t); var m=Math.floor(t/60), s=Math.floor(t%60); return m+':'+(s<10?'0':'')+s; }
function updateCount(){ var n=0; DATA.forEach(function(d){ if(state[d.stem] && state[d.stem].decision) n++; }); document.getElementById('count').textContent = n+' of '+DATA.length+' decided'; }

function linesOf(d){ var s=st(d.stem); return s.lines || d.sheet.slice(); }

function renderSheet(d, box){
  box.innerHTML='';
  var lines = linesOf(d);
  lines.forEach(function(t,i){
    var inp = el('input',{type:'text','data-stem':d.stem,'data-i':i}); inp.value=t;
    inp.addEventListener('input', function(){ var s=st(d.stem); var L=linesOf(d); L[i]=inp.value; s.lines=L; save(); });
    var add = el('button',{text:'+',title:'Add a line below',type:'button'});
    add.addEventListener('click', function(){ var s=st(d.stem); var L=linesOf(d); L.splice(i+1,0,''); s.lines=L; save(); renderSheet(d,box); });
    var del = el('button',{text:'x',title:'Remove this line',type:'button'});
    del.addEventListener('click', function(){ var s=st(d.stem); var L=linesOf(d); L.splice(i,1); s.lines=L; save(); renderSheet(d,box); });
    box.appendChild(el('div',{cls:'ln'},[el('span',{cls:'n',text:String(i+1)}),inp,add,del]));
  });
}

function render(){
  var root=document.getElementById('root'); root.innerHTML='';
  var clean=el('details',{cls:'clean-box'},[el('summary',{text:'Clean arrangements (no findings) - open to check'})]);
  var cleanAny=false;
  DATA.forEach(function(d){
    var sec=el('section',{cls:'arr',id:'a-'+d.stem});
    var h=el('h2',{text:d.title+' - '+d.label}); h.appendChild(el('span',{cls:'badge '+d.status,text:d.status}));
    sec.appendChild(h);
    sec.appendChild(el('div',{cls:'meta',text:d.stem+'   |   direct match '+d.direct+'%   |   whisper '+d.model}));
    var a=el('audio',{controls:'controls',preload:'none',src:MEDIA+d.file}); sec.appendChild(a);
    if(!d.findings.length) sec.appendChild(el('p',{text:'No findings from the audit.'}));
    d.findings.forEach(function(f,fi){
      var id=f.kind+'-'+fi;
      var box=el('div',{cls:'finding '+f.kind});
      var head=el('div',{});
      head.appendChild(el('span',{cls:'kind',text:f.kind+'   '}));
      head.appendChild(document.createTextNode(f.what+' '));
      var pb=el('button',{type:'button',text: f.t==null ? 'No time available' : 'Play from '+mmss(f.t)});
      if(f.t==null) pb.disabled=true;
      pb.addEventListener('click', function(){ document.querySelectorAll('audio').forEach(function(x){ if(x!==a) x.pause(); }); a.currentTime=Math.max(0,f.t-2); a.play(); });
      head.appendChild(pb);
      box.appendChild(head);
      box.appendChild(el('div',{cls:'cols'},[
        el('div',{cls:'col'},[el('h4',{text:'On the sheet ('+f.sheet_note+')'}),el('div',{text:f.sheet})]),
        el('div',{cls:'col'},[el('h4',{text:'Heard in the recording'}),el('div',{text:f.heard})])
      ]));
      box.appendChild(el('div',{cls:'draft',text:'Proposed line - draft, not confirmed (edit freely):'}));
      var ta=el('textarea',{}); var s=st(d.stem);
      ta.value = (s.proposals[id]!==undefined) ? s.proposals[id] : f.proposal;
      ta.addEventListener('input', function(){ st(d.stem).proposals[id]=ta.value; save(); });
      box.appendChild(ta);
      sec.appendChild(box);
    });
    sec.appendChild(el('h3',{text:'Full sheet for this recording (editable)'}));
    var sb=el('div',{cls:'sheet'}); sec.appendChild(sb); renderSheet(d,sb);
    var dec=el('div',{cls:'decide'});
    [['correct','Sheet is correct as-is'],['edits','Use my edits'],['hold','Not sure - hold']].forEach(function(p){
      var b=el('button',{type:'button','data-d':p[0],text:p[1]});
      if(p[0]==='hold') b.className='hold';
      function paint(){ var on = st(d.stem).decision===p[0]; b.classList.toggle('on',on); }
      b.addEventListener('click', function(){ st(d.stem).decision = (st(d.stem).decision===p[0]) ? null : p[0]; save(); dec.querySelectorAll('button').forEach(function(x){ x.classList.toggle('on', st(d.stem).decision===x.getAttribute('data-d')); }); });
      dec.appendChild(b); paint();
    });
    sec.appendChild(dec);
    if(d.status==='clean'){ clean.appendChild(sec); cleanAny=true; } else root.appendChild(sec);
  });
  if(cleanAny) root.appendChild(clean);
  updateCount();
}

document.getElementById('export').addEventListener('click', function(){
  var out={exported:new Date().toISOString(),audit_date:DATE,arrangements:[]};
  DATA.forEach(function(d){
    var s=state[d.stem]||{}; var edited=false;
    if(s.lines){ edited = JSON.stringify(s.lines)!==JSON.stringify(d.sheet); }
    var rec={stem:d.stem,decision:s.decision||null};
    if(edited) rec.lines=s.lines;
    var props={}; var any=false;
    Object.keys(s.proposals||{}).forEach(function(k){ props[k]=s.proposals[k]; any=true; });
    if(any) rec.proposal_edits=props;
    out.arrangements.push(rec);
  });
  var blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'});
  var a=document.createElement('a'); a.href=URL.createObjectURL(blob);
  a.download='WoP_Lyric_Decisions_'+DATE+'.json'; document.body.appendChild(a); a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); },500);
});
load(); render();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit")
    args = ap.parse_args()
    audit = args.audit or sorted((REPO / "tools" / "reports").glob("lyric_audit_*.json"))[-1]
    date, items = build(audit)
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    html = (PAGE.replace("__DATE__", date).replace("__MEDIA__", MEDIA).replace("__DATA__", data))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"WoP_Lyric_Review_{date}.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(items)} arrangements, {out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
