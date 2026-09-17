import json,sys,warnings,os,re; warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,r'C:\Users\aaron\Documents\words-of-plainness\scripts')
SP=os.path.dirname(os.path.abspath(__file__))
for tag in ('sb_p2','sb_p3'):
    p=json.load(open(os.path.join(SP,tag,'lutheran.json'),encoding='utf-8'))
    for c in p['cards']:
        if c['queue_id'] in ('Q-163','Q-195','Q-227'):
            print('==',tag,c['queue_id'],c['predicate'])
            for e in c['candidates']+[r for r in c['rejections'] if r.get('stage')=='tier allocation']:
                h=e.get('registered_phrase_hit') or {}
                print('   ', 'SEAT' if e in c['candidates'] else 'CUT ', e['candidate_id'].split('-p1-')[1], e['effective_tier'], '|', e['phrase'], '| hit:', h.get('registry_id'), h.get('locator'))
from sjn_recovery import store
from sjn_recovery.textutil import punct_key
cr=[c for c in json.load(open(os.path.join(SP,'chunks_after','BSR-LU-01.json'),encoding='utf-8')) if c['locator']=='Small Catechism: II. The Creed, ¶1–3'][0]
print(cr['text'][:600])
lu03=store.load_chunks('BSR-LU-03'); lu01=json.load(open(os.path.join(SP,'chunks_after','BSR-LU-01.json'),encoding='utf-8'))
keys={c['locator']:punct_key(c['text']) for c in lu01}
for c in lu03:
    print('LU-03 chunk', c['locator'], '| identical to an LU-01 chunk:', any(punct_key(c['text'])==k for k in keys.values()))
    for s in [s for s in re.split(r'(?<=[.?!;])\s+', c['text']) if s.strip()]:
        hits=[l for l,k in keys.items() if punct_key(s) and punct_key(s) in k]
        print('   ', 'VERBATIM' if hits else 'not     ', '|', s[:120], '|', hits[:3])
