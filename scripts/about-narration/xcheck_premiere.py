import json, re, difflib
from pathlib import Path
D = Path(r'C:\Users\aaron\Documents\wop-scratch\about'); W = D/'work'
raw = (D/'premiere_transcript.srt').read_text(encoding='utf-8-sig')
ts = lambda s: (lambda h,m,r: int(h)*3600+int(m)*60+int(r[:2])+int(r[3:])/1000)(*s.split(':'))
norm = lambda t: [x for x in re.split(r"[^a-z0-9']+", t.lower().replace('’',"'")) if x]
cues = []
for b in re.split(r'\n\s*\n', raw.strip()):
    L = b.strip().splitlines()
    if len(L) < 3: continue
    cues.append((ts(L[1].split(' --> ')[0]), ' '.join(L[2:])))
aw = json.loads((W/'aligned_words.json').read_text(encoding='utf-8'))
NUM = {'26':'twenty six','31':'thirty one','1622':'sixteen twenty two','11':'eleven','r':'rv'}
stok, smap = [], []
for k, w in enumerate(aw):
    for t in norm(w['w']): stok.append(t); smap.append(k)
ptok, pcue = [], []
for ci, (t0, txt) in enumerate(cues):
    for t in norm(txt): ptok.append(t); pcue.append(ci)
sm = difflib.SequenceMatcher(None, ptok, stok, autojunk=False)
first = {}
for a, b, n in sm.get_matching_blocks():
    for k in range(n):
        first.setdefault(pcue[a+k], (smap[b+k], ptok[a+k]))
dev = []; ds = []
for ci, (t0, txt) in enumerate(cues):
    if ci not in first: dev.append((round(t0,2), 'UNMATCHED', txt[:40])); continue
    k, tok = first[ci]; d = aw[k]['start'] - t0; ds.append(d)
    if abs(d) > 1.0: dev.append((round(t0,2), round(d,2), tok, txt[:40]))
ds.sort()
print(len(cues), 'premiere cues;', len(ds), 'matched; delta (aligned word start - cue start) min %.2f median %.2f max %.2f' % (ds[0], ds[len(ds)//2], ds[-1]))
print('cues outside 1.0 s:', dev)
