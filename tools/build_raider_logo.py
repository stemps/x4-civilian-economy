"""Encode the approved PNG as X4's gzip-wrapped BGRA DDS with mipmaps.

Requires Pillow. This is format/size conversion only; source artwork is unchanged.
"""
from pathlib import Path
import gzip
import io
import struct
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = Image.open(ROOT / 'images/ce_unrest_skull.png').convert('RGBA')
    image = source.resize((256, 256), Image.Resampling.LANCZOS)
    levels = []
    header = None
    while True:
        buffer = io.BytesIO()
        image.save(buffer, format='DDS')
        data = buffer.getvalue()
        if header is None:
            header = bytearray(data[:128])
        levels.append(data[128:])
        if image.width == 1:
            break
        image = image.resize((image.width // 2, image.height // 2), Image.Resampling.LANCZOS)
    # DDSD_MIPMAPCOUNT, DDSCAPS_COMPLEX and DDSCAPS_MIPMAP.
    struct.pack_into('<I', header, 8, struct.unpack_from('<I', header, 8)[0] | 0x20000)
    struct.pack_into('<I', header, 28, len(levels))
    struct.pack_into('<I', header, 108, struct.unpack_from('<I', header, 108)[0] | 0x400008)
    payload = bytes(header) + b''.join(levels)
    target = ROOT / 'assets/textures/ui/factions/ce_unrest_skull.gz'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(gzip.compress(payload, mtime=0))
    with Image.open(io.BytesIO(gzip.decompress(target.read_bytes()))) as decoded:
        assert decoded.size == (256, 256) and decoded.mode == 'RGBA'
        assert decoded.getchannel('A').getextrema() == (0, 255)
    print(f'Encoded {target.relative_to(ROOT)}: 256x256 RGBA, {len(levels)} mip levels')


if __name__ == '__main__':
    main()
