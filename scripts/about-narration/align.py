import json, os, sys, requests
from pathlib import Path
cands = [Path(os.environ['APPDATA'])/'Claude'/'claude_desktop_config.json']
key = None
for c in cands:
    if c.exists():
        cfg = json.loads(c.read_text(encoding='utf-8'))
        for name, s in cfg.get('mcpServers', {}).items():
            k = (s.get('env') or {}).get('ELEVENLABS_API_KEY')
            if k and k.startswith('sk_'): key = k; print('key from', name); break
if not key: sys.exit('no sk_ key found')
W = Path(r'C:\Users\aaron\Documents\wop-scratch\about\work')
audio = Path(r'C:\Users\aaron\Documents\wop-scratch\about\encoded\about-narration.m4a')
text = (W/'alignment_text.txt').read_text(encoding='utf-8').strip()
r = requests.post('https://api.elevenlabs.io/v1/forced-alignment', headers={'xi-api-key': key},
                  files={'file': (audio.name, audio.open('rb'), 'audio/mp4')}, data={'text': text}, timeout=600)
print(r.status_code)
(W/'alignment_raw.json').write_text(r.text, encoding='utf-8')
if r.ok:
    j = r.json(); print(list(j.keys()), len(j.get('words', [])), 'loss', j.get('loss'))
else: print(r.text[:500])
