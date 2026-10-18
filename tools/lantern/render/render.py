#!/usr/bin/env python3
"""Render one Lantern Post.

    python tools/lantern/render/render.py SPEC.json --out OUT_DIR [--media-dir DIR] [--keep-work]

Reads the spec, the background image, the narration and the music bed (file names in the spec are
looked up in --media-dir, which defaults to the spec's own folder). Writes OUT_DIR/out.mp4,
cover_9x16.png, check.json and check.md. Exit code 0 only when every standard check passes."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lantern_render.media import MediaError  # noqa: E402
from lantern_render.pipeline import render  # noqa: E402
from lantern_render.spec import SpecError  # noqa: E402
from lantern_render.timing import TimingError  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec')
    ap.add_argument('--out', required=True)
    ap.add_argument('--media-dir')
    ap.add_argument('--keep-work', action='store_true')
    a = ap.parse_args(argv)
    try:
        check = render(a.spec, a.out, a.media_dir, a.keep_work)
    except (SpecError, TimingError, MediaError) as e:
        print(f'STOPPED: {e}', file=sys.stderr)
        return 2
    print(Path(a.out, 'check.md').read_text(encoding='utf-8'))
    return 0 if check['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
