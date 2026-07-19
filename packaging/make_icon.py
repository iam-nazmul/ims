"""Generate the app icon (ims.png / ims.ico / ims.icns) into packaging/icons.

Crops the box-mark from media/icons/Logo.png, renders it at each size with Qt,
then packs PNG-based .ico and .icns containers by hand so no extra image
libraries are needed. Also writes media/icons/appicon.png for the runtime
window icon.
"""

from __future__ import annotations

import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QGuiApplication, QImage, QPainter, qAlpha

PACKAGING = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(os.path.dirname(PACKAGING), "media", "icons", "Logo.png")


def crop_mark(src: QImage) -> QImage:
    """Return the leftmost glyph of the logo (the box mark, without the text)."""
    w, h = src.width(), src.height()
    filled = [any(qAlpha(src.pixel(x, y)) > 8 for y in range(h)) for x in range(w)]
    x0 = next((x for x in range(w) if filled[x]), 0)
    x1 = w - 1
    gap = 0
    for x in range(x0, w):
        gap = gap + 1 if not filled[x] else 0
        if gap >= max(4, w // 100) and x - gap - x0 >= w // 5:
            x1 = x - gap
            break
    ys = [y for y in range(h)
          if any(qAlpha(src.pixel(x, y)) > 8 for x in range(x0, x1 + 1))]
    return src.copy(x0, ys[0], x1 - x0 + 1, ys[-1] - ys[0] + 1)


def render(mark: QImage, size: int) -> bytes:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    m = size * 0.04
    avail = size - 2 * m
    scale = min(avail / mark.width(), avail / mark.height())
    tw, th = mark.width() * scale, mark.height() * scale
    p.drawImage(QRectF((size - tw) / 2, (size - th) / 2, tw, th), mark)
    p.end()

    from PySide6.QtCore import QBuffer, QIODevice
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def write_ico(path: str, pngs: dict[int, bytes]):
    entries, blobs, offset = [], [], 6 + 16 * len(pngs)
    for size, data in sorted(pngs.items()):
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0,
                                   1, 32, len(data), offset))
        blobs.append(data)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(pngs)))
        f.writelines(entries)
        f.writelines(blobs)


def write_icns(path: str, pngs: dict[int, bytes]):
    types = {128: b"ic07", 256: b"ic08", 512: b"ic09"}
    body = b""
    for size, data in sorted(pngs.items()):
        if size in types:
            body += types[size] + struct.pack(">I", len(data) + 8) + data
    with open(path, "wb") as f:
        f.write(b"icns" + struct.pack(">I", len(body) + 8) + body)


def main() -> int:
    QGuiApplication([])
    src = QImage(LOGO)
    if src.isNull():
        print(f"Cannot read {LOGO}", file=sys.stderr)
        return 1
    mark = crop_mark(src.convertToFormat(QImage.Format.Format_ARGB32))
    out = os.path.join(PACKAGING, "icons")
    os.makedirs(out, exist_ok=True)
    pngs = {s: render(mark, s) for s in (16, 32, 48, 128, 256, 512)}
    with open(os.path.join(out, "ims.png"), "wb") as f:
        f.write(pngs[256])
    with open(os.path.join(os.path.dirname(LOGO), "appicon.png"), "wb") as f:
        f.write(pngs[256])
    write_ico(os.path.join(out, "ims.ico"), {s: pngs[s] for s in (16, 32, 48, 256)})
    write_icns(os.path.join(out, "ims.icns"), pngs)
    print(f"Icons written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
