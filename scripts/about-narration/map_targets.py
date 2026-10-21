import json, re, difflib, sys
from html.parser import HTMLParser
from pathlib import Path
W = Path(r'C:\Users\aaron\Documents\wop-scratch\about\work')
html = Path(r'C:\Users\aaron\Documents\words-of-plainness\_site\about\index.html').read_text(encoding='utf-8')

class P(HTMLParser):
    def __init__(s): super().__init__(); s.cur = None; s.t = {}; s.order = []
    def handle_starttag(s, tag, a):
        d = dict(a)
        if 'data-narr' in d: s.cur = d['data-narr']; s.t[s.cur] = ''; s.order.append(s.cur)
    def handle_endtag(s, tag):
        if tag == 'span' and s.cur is not None and s.depth_end: pass
    def handle_data(s, d):
        if s.cur: s.t[s.cur] += d
P.depth_end = False
# spans are never nested and contain no <span>, so close on the first </span>
class P2(P):
    def handle_endtag(s, tag):
        if tag == 'span': s.cur = None
p = P2(); p.feed(html)
targets = [(i, re.sub(r'\s+', ' ', p.t[i]).strip()) for i in p.order]
print(len(targets), 'targets in built HTML')

norm = lambda t: [x for x in re.split(r"[^a-z0-9']+", t.lower().replace('’', "'").replace('“','').replace('”','')) if x]
aw = json.loads((W/'aligned_words.json').read_text(encoding='utf-8'))
stok, smap = [], []
for k, w in enumerate(aw):
    for t in norm(w['w']): stok.append(t); smap.append(k)
ptok, pmap = [], []
for ti, (i, txt) in enumerate(targets):
    for t in norm(txt): ptok.append(t); pmap.append(ti)
sm = difflib.SequenceMatcher(None, ptok, stok, autojunk=False)
matches = {}  # target idx -> list of spoken word idx
for a, b, n in sm.get_matching_blocks():
    for k in range(n): matches.setdefault(pmap[a+k], []).append(smap[b+k])
print('matched page tokens: %d / %d' % (sum(len(v) for v in matches.values()), len(ptok)))

words = [w['w'] for w in aw]
def find_seq(seq, after=0):
    for k in range(after, len(words) - len(seq) + 1):
        if [x.lower().strip('.,"') for x in words[k:k+len(seq)]] == seq: return k
    raise SystemExit('anchor not found ' + str(seq))
by = [k for k in range(len(words)-2) if [x.lower().strip(',') for x in words[k:k+3]] == ['by','the','way']]
print('"By the way" at word idx', by, [round(aw[k]['start'],2) for k in by])

first, last = {}, {}
missing = []
for ti, (i, txt) in enumerate(targets):
    m = sorted(matches.get(ti, []))
    if not m: missing.append(i); continue
    first[i], last[i] = m[0], m[-1]
if missing: print('NO ALIGNED TIMING FOR', missing); sys.exit(2)

# rulings 1-2: the asides begin at "By the way"; they end at their last spoken word.
assert len(by) == 2
first['collage-cap'] = by[0]; first['workspace-cap'] = by[1]
last['collage-cap'] = find_seq(['one','mind'], by[0]) + 1
last['workspace-cap'] = find_seq(['my','wife'], by[1]) + 1
# ruling 4: signature "Your Brother, Aaron Powner."
sg = find_seq(['your','brother,'.strip(',')], len(words)-8) if False else len(words)-4
assert [x.lower().strip('.,') for x in words[sg:]] == ['your','brother','aaron','powner'], words[sg:]
first['sig'], last['sig'] = sg, len(words)-1

# Partition: each target owns the spoken words from its own start up to the next target's start.
ids = [i for i, _ in targets]
starts = [first[i] for i in ids]
bad = [(ids[k], starts[k], starts[k+1]) for k in range(len(ids)-1) if starts[k+1] <= starts[k]]
print('non-monotonic starts:', bad)
out = {}
for k, i in enumerate(ids):
    s = first[i]
    nxt = starts[k+1] if k+1 < len(ids) else len(words)
    e = max(last[i], s)
    # words between this target's last matched word and the next start belong to this target only if
    # they are unmatched extras (e.g. a spoken citation); clamp to nxt-1
    e = min(max(e, nxt-1), len(words)-1) if k+1 < len(ids) else len(words)-1
    out[i] = {'start': round(aw[s]['start'], 3), 'end': round(aw[e]['end'], 3), 'words': [s, e], 'matched': len(matches.get(targets[k][0] and k, [])) if False else None}
for i in out: del out[i]['matched']
(W/'target_timing_draft.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
for i, _ in targets:
    t = out[i]; k = ids.index(i)
    print(f"{i:14s} {t['start']:8.2f} {t['end']:8.2f}  {' '.join(words[t['words'][0]:t['words'][1]+1])[:70]}")
