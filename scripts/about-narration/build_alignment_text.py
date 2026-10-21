# Build the forced-alignment text from the five SRT scripts.
# Concatenate in order; strip bracketed tags; restore respellings; join split cues.
import re, json, sys
from pathlib import Path
D = Path(r'C:\Users\aaron\Documents\wop-scratch\about')
W = D / 'work'
RESPELL = {'Mel-KIZ-uh-dek': 'Melchizedek', 'Nee-fye': 'Nephi'}

def ts(s):
    h, m, r = s.split(':'); sec, ms = r.split(',')
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

words = []   # provenance per spoken word
cues = []    # per cue with spoken text
for seg in range(1, 6):
    raw = (D / f'About_0{seg}.srt').read_text(encoding='utf-8-sig')
    for block in re.split(r'\n\s*\n', raw.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3: continue
        a, b = lines[1].split(' --> ')
        text = ' '.join(l.strip() for l in lines[2:])
        text = re.sub(r'\[[^\]]*\]', ' ', text)          # bracketed performance tags
        for k, v in RESPELL.items(): text = text.replace(k, v)
        text = text.replace('—', ' ').replace('...', '.')
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)     # tag removal leaves " ." (never touch opening quotes)
        text = re.sub(r'([.!?])\.+', r'\1', text)        # "plainly. [pause]." would leave ".."
        text = re.sub(r'^[.\s]+$', '', text)
        if not text: continue
        ci = len(cues)
        cues.append({'seg': seg, 'idx': int(lines[0]), 'start': ts(a), 'end': ts(b), 'text': text})
        for w in text.split():
            words.append({'seg': seg, 'cue': ci, 'cue_start': ts(a), 'word': w})

text = ' '.join(w['word'] for w in words)
(W / 'alignment_text.txt').write_text(text + '\n', encoding='utf-8')
(W / 'alignment_provenance.json').write_text(json.dumps({'cues': cues, 'words': words}, ensure_ascii=False, indent=1), encoding='utf-8')
print(len(cues), 'cues,', len(words), 'words,', len(text), 'chars')
left = [w['word'] for w in words if re.search(r'[a-z]-[A-Z]|[A-Z]{3,}', w['word']) and w['word'] not in ('AI','ChatGPT')]
print('suspect respellings left:', left)
print(text[:400])
