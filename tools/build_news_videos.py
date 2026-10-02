"""Encode broadcast art as news clips with a separate, deterministic lower third.

Requires imageio-ffmpeg. --font accepts a TrueType font (defaults to Windows Arial).
Captions remain native MD text; scrolling ticker strings come from the English t file.
The source PNGs are never edited, cropped or overwritten.
"""
import argparse
from pathlib import Path
import subprocess
from xml.etree import ElementTree as E

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'src'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font', type=Path, default=Path('C:/Windows/Fonts/arialbd.ttf'))
    args = parser.parse_args()
    if not args.font.is_file():
        parser.error('Supply an installed TrueType font with --font')
    font = args.font.resolve().as_posix().replace(':', r'\:').replace("'", r"\'")
    strings = {int(t.get('id')): ''.join(t.itertext())
               for t in E.parse(MOD / 't/0001-l044.xml').iter('t')}
    scratch = ROOT / '.cache/news-text'
    scratch.mkdir(parents=True, exist_ok=True)
    (ROOT / 'output').mkdir(exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for kind, artwork, text_id in [('raid', 'pirate-mobilisation', 291),
                                   ('sabotage', 'station-sabotage', 292),
                                   ('hacking', 'station-hacking', 292)]:
        (scratch / f'{kind}-ticker.txt').write_text(
            f'{strings[296]}: {strings[text_id]}'.upper(), encoding='utf-8')
        # Fit the entire approved image above the strip; never obscure module tips.
        filters = (
            'scale=1280:636:force_original_aspect_ratio=decrease:force_divisible_by=2,'
            'pad=1280:720:(ow-iw)/2:0:color=0x080d13,'
            'drawbox=x=0:y=636:w=iw:h=84:color=0xb32a2e:t=fill'
        )
        # Two copies form a continuous right-to-left ticker, 110 pixels/sec.
        for offset in ('28', 'tw+128'):
            filters += (
                f",drawtext=fontfile='{font}':textfile='.cache/news-text/{kind}-ticker.txt':"
                'expansion=none:fontsize=38:fontcolor=white:'
                f"x='{offset}-mod(t*110,tw+100)':y=636+(84-th)/2"
            )
        source = ROOT / f'images/broadcast/{artwork}.png'
        # Extension root: WorkshopTool refuses a videos/ folder.
        destination = MOD / f'ce_news_{kind}.mkv'
        temporary = destination.with_name(destination.stem + '.tmp' + destination.suffix)
        subprocess.run([ffmpeg, '-y', '-hide_banner', '-loglevel', 'error',
                        '-loop', '1', '-framerate', '24', '-i', str(source),
                        '-vf', filters, '-t', '12', '-an', '-c:v', 'libx264',
                        '-profile:v', 'baseline', '-pix_fmt', 'yuv420p', '-crf', '18',
                        '-preset', 'medium', str(temporary)], cwd=ROOT, check=True)
        reader = imageio_ffmpeg.read_frames(str(temporary))
        metadata = next(reader)
        try:
            frames = sum(1 for _ in reader)
        finally:
            reader.close()
        assert metadata['size'] == (1280, 720) and metadata['fps'] == 24, metadata
        assert metadata['codec'] == 'h264' and abs(metadata['duration'] - 12) < .05, metadata
        assert frames == 288, frames
        temporary.replace(destination)
        subprocess.run([ffmpeg, '-y', '-hide_banner', '-loglevel', 'error',
                        '-i', str(destination), '-frames:v', '1',
                        str(ROOT / 'output' / (destination.stem + '.png'))], check=True)
        print(f'{destination.name}: full decode passed, {frames} frames, {metadata}')


if __name__ == '__main__':
    main()
