import json
from pathlib import Path
W = Path(r'C:\Users\aaron\Documents\wop-scratch\about\work')
raw = json.loads((W/'alignment_raw.json').read_text(encoding='utf-8'))
prov = json.loads((W/'alignment_provenance.json').read_text(encoding='utf-8'))
aw = [w for w in raw['words'] if w['text'].strip()]
assert len(aw) == len(prov['words']), (len(aw), len(prov['words']))
bad = [(i, a['text'], p['word']) for i, (a, p) in enumerate(zip(aw, prov['words'])) if a['text'] != p['word']]
print('token mismatches:', bad[:5], len(bad))
out = [{'i': i, 'w': a['text'], 'start': a['start'], 'end': a['end'], 'loss': a.get('loss'), **{k: p[k] for k in ('seg','cue','cue_start')}} for i, (a, p) in enumerate(zip(aw, prov['words']))]
(W/'aligned_words.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
import statistics
ls = sorted(o['loss'] for o in out)
print('loss median %.3f p95 %.3f max %.3f' % (statistics.median(ls), ls[int(.95*len(ls))], ls[-1]))
print('worst:', [(o['w'], round(o['start'],2), round(o['loss'],2)) for o in sorted(out, key=lambda o:-o['loss'])[:8]])
print('first', out[0]['start'], 'last end', out[-1]['end'])
# monotonic + gaps
prev = 0; gaps = []
for o in out:
    if o['start'] < prev - 1e-6: print('non-monotonic at', o['i'], o['w'])
    if o['start'] - prev > 1.5: gaps.append((round(prev,2), round(o['start'],2), o['w']))
    prev = o['end']
print('gaps >1.5s:', gaps)
# (a) per-segment offsets: aligned first-word start of each cue vs SRT cue start
import collections
segoff = collections.defaultdict(list)
seen = set()
for o in out:
    if o['cue'] in seen: continue
    seen.add(o['cue']); segoff[o['seg']].append((o['cue'], o['start'] - o['cue_start'], o['w']))
cues = prov['cues']
for s, lst in segoff.items():
    offs = sorted(x[1] for x in lst); med = offs[len(offs)//2]
    dev = [(cues[c]['seg'], cues[c]['idx'], round(cues[c]['start'],2), w, round(d-med,2)) for c, d, w in lst if abs(d-med) > 0.5]
    print(f'seg {s}: n={len(lst)} median offset {med:.3f}s  spread {offs[0]-med:.2f}..{offs[-1]-med:.2f}  >0.5s deviations: {dev}')
