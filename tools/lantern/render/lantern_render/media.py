"""Thin wrappers around ffmpeg / ffprobe."""
import json
import os
import re
import shutil
import subprocess


class MediaError(RuntimeError):
    pass


def _bin(name):
    p = os.environ.get('LANTERN_' + name.upper()) or shutil.which(name)
    if not p:
        raise MediaError(f'{name} not found on PATH (set LANTERN_{name.upper()} to its location)')
    return p


def run(args, cwd=None, check=True):
    """Run an ffmpeg-family command; return (returncode, stderr text)."""
    r = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
    if check and r.returncode != 0:
        raise MediaError('command failed: %s\n%s' % (' '.join(map(str, args[:6])), r.stderr[-1500:]))
    return r.returncode, r.stderr


def ffmpeg(*args, cwd=None, check=True):
    return run([_bin('ffmpeg'), '-hide_banner', '-nostats', '-y', *map(str, args)], cwd=cwd, check=check)


def ffprobe_json(path):
    r = subprocess.run([_bin('ffprobe'), '-v', 'error', '-print_format', 'json', '-show_format',
                        '-show_streams', str(path)], stdin=subprocess.DEVNULL, capture_output=True,
                       text=True, encoding='utf-8')
    if r.returncode != 0:
        raise MediaError(f'ffprobe could not read {path}: {r.stderr.strip()[:300]}')
    return json.loads(r.stdout)


def duration(path):
    info = ffprobe_json(path)
    d = info.get('format', {}).get('duration')
    if d is None:
        raise MediaError(f'no duration for {path}')
    return float(d)


def loudnorm_stats(path, start=None, length=None, filters=''):
    """First-pass loudnorm measurement: dict with input_i, input_tp, input_lra, input_thresh, target_offset."""
    pre = []
    if start is not None:
        pre += ['-ss', str(start)]
    if length is not None:
        pre += ['-t', str(length)]
    af = (filters + ',' if filters else '') + 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json'
    _, err = ffmpeg(*pre, '-i', path, '-af', af, '-f', 'null', '-')
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', err, re.S)
    if not m:
        raise MediaError('could not read loudness of %s' % path)
    return {k: float(v) for k, v in json.loads(m.group(0)).items() if _isnum(v)}


def _isnum(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False
