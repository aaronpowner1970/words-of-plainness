"""Line timing: pause detection first, forced alignment as the fallback.

Never guesses: if neither method produces one onset per spoken line it raises TimingError."""
import re
import wave
from concurrent.futures import ThreadPoolExecutor

from . import media

DEFAULT_SETTING = (-35, 0.35)  # silencedetect noise dB, minimum silence seconds
NOISE_RANGE = range(-40, -29)  # -40 .. -30 dB
MIN_SILENCE_RANGE = (0.30, 0.35, 0.40)
MAX_ONSET_SPREAD = 0.25  # settings that agree on the count must also agree on the onsets


class TimingError(RuntimeError):
    pass


# ---------------- pure functions (tested without audio) ----------------

def speech_segments(silences, total):
    """Complement of the silences within [0, total]. Segments shorter than 20 ms are dropped."""
    segs, pos = [], 0.0
    for s, e in sorted(silences):
        if s - pos > 0.02:
            segs.append((pos, s))
        pos = max(pos, e)
    if total - pos > 0.02:
        segs.append((pos, total))
    return segs


def choose_pause_timing(candidates, n_expected, default=DEFAULT_SETTING):
    """candidates: {(noise_db, min_silence): [(start, end), ...]} speech segments per setting.
    Return a dict for the setting closest to `default` that yields exactly n_expected segments,
    or None when no setting does or the matching settings disagree on where lines start."""
    good = {k: v for k, v in candidates.items() if len(v) == n_expected}
    if not good:
        return None
    onsets = [[s for s, _ in v] for v in good.values()]
    spread = max(max(col) - min(col) for col in zip(*onsets))
    if spread > MAX_ONSET_SPREAD:
        return None
    key = min(good, key=lambda k: (abs(k[0] - default[0]) / 5 + abs(k[1] - default[1]) / 0.05, k))
    return {'setting': key, 'segments': good[key], 'settings_agreeing': len(good),
            'settings_tried': len(candidates), 'onset_spread': round(spread, 3)}


def first_speech_after(silences, total, after):
    """Start of the first speech activity that begins at or after `after`, or None."""
    for s, _ in speech_segments(silences, total):
        if s >= after:
            return s
    return None


# ---------------- audio-backed methods ----------------

def detect_silences(path, noise_db, min_silence):
    _, err = media.ffmpeg('-i', path, '-af', f'silencedetect=noise={noise_db}dB:d={min_silence}',
                          '-f', 'null', '-')
    sil, start = [], None
    for line in err.splitlines():
        m = re.search(r'silence_start: (-?[\d.]+)', line)
        if m:
            start = max(0.0, float(m.group(1)))
        m = re.search(r'silence_end: ([\d.]+)', line)
        if m and start is not None:
            sil.append((start, float(m.group(1))))
            start = None
    if start is not None:
        sil.append((start, float('inf')))
    return sil


LEAD_MIN_SILENCE = 0.05  # a short silence at the very start still moves the first onset


def leading_silence_end(path, noise_db):
    """End of silence that begins at 0, however short, or None when the file starts with sound."""
    sil = detect_silences(path, noise_db, LEAD_MIN_SILENCE)
    return sil[0][1] if sil and sil[0][0] <= 0.001 else None


def pause_timing(path, n_expected, total):
    grid = [(n, d) for n in NOISE_RANGE for d in MIN_SILENCE_RANGE]
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda k: detect_silences(path, *k), grid))
        leads = dict(zip(NOISE_RANGE, ex.map(lambda n: leading_silence_end(path, n), NOISE_RANGE)))
    cands = {}
    for k, sil in zip(grid, results):
        segs = speech_segments([(s, min(e, total)) for s, e in sil], total)
        lead = leads[k[0]]
        if segs and lead is not None and segs[0][0] < lead < segs[0][1]:
            segs[0] = (lead, segs[0][1])
        cands[k] = segs
    pick = choose_pause_timing(cands, n_expected)
    if pick is None:
        counts = sorted({len(v) for v in cands.values()})
        raise TimingError('pause detection found %s speech segments across the tried settings, not %d'
                          % (counts, n_expected))
    return pick


def align_timing(path, line_words, workdir):
    """Forced alignment of the spoken text (pocketsphinx). Returns per-line onsets and ends."""
    try:
        from pocketsphinx import Decoder
    except ImportError as e:
        raise TimingError('forced alignment needs pocketsphinx (pip install pocketsphinx): %s' % e)
    wav = f'{workdir}/align16k.wav'
    media.ffmpeg('-i', path, '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', wav)
    words = [w for lw in line_words for w in lw]
    try:
        dec = Decoder(samprate=16000, bestpath=False)
        dec.set_align_text(' '.join(words))
        with wave.open(wav, 'rb') as w:
            data = w.readframes(w.getnframes())
        dec.start_utt()
        dec.process_raw(data, full_utt=True)
        dec.end_utt()
        segs = [(re.sub(r'\(\d+\)$', '', s.word), s.start_frame / 100.0, (s.end_frame + 1) / 100.0)
                for s in dec.seg()]
    except Exception as e:  # unknown word in the dictionary, decoder failure
        raise TimingError('forced alignment failed: %s' % e)
    spoken = [s for s in segs if not (s[0].startswith('<') or s[0].startswith('['))]
    if [s[0] for s in spoken] != words:
        raise TimingError('forced alignment returned %d words for %d spoken words' % (len(spoken), len(words)))
    onsets, ends, i = [], [], 0
    for lw in line_words:
        onsets.append(spoken[i][1])
        ends.append(spoken[i + len(lw) - 1][2])
        i += len(lw)
    if any(b < a for a, b in zip(onsets, onsets[1:])):
        raise TimingError('forced alignment gave out-of-order onsets')
    return onsets, ends


def measure_timing(path, line_words, url_spoken, mode, workdir, total):
    """Choose the method and return a dict: method, onsets, ends, speech_end, url_onset, notes."""
    n = len(line_words)
    notes, result = [], None
    if mode in ('auto', 'pause'):
        try:
            pick = pause_timing(path, n + (1 if url_spoken else 0), total)
            segs = pick['segments'][:n]
            result = {'method': 'pause detection', 'onsets': [s for s, _ in segs], 'ends': [e for _, e in segs],
                      'detail': {k: pick[k] for k in ('setting', 'settings_agreeing', 'settings_tried', 'onset_spread')}}
        except TimingError as e:
            notes.append(f'pause detection not used: {e}')
            if mode == 'pause':
                raise
    if result is None:
        on, en = align_timing(path, line_words, workdir)
        result = {'method': 'forced alignment (pocketsphinx)', 'onsets': on, 'ends': en, 'detail': {}}
    result['speech_end'] = result['ends'][-1]
    sil = detect_silences(path, *DEFAULT_SETTING)
    sil = [(s, min(e, total)) for s, e in sil]
    result['url_onset'] = first_speech_after(sil, total, result['speech_end'] + 0.05) if url_spoken else None
    # sanity: every onset must sit in or just before audible speech
    speech = speech_segments(sil, total)
    for i, o in enumerate(result['onsets']):
        if not any(s - 0.4 <= o <= e + 0.05 for s, e in speech):
            raise TimingError('line %d onset %.2f s is not in audible speech' % (i + 1, o))
    result['notes'] = notes
    return result
