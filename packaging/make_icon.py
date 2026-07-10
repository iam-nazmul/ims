"""Generate the app icon (ims.png / ims.ico / ims.icns) into packaging/icons.

Draws a simple "IMS" tile with Qt, then packs PNG-based .ico and .icns
containers by hand so no extra image libraries are needed.
"""

from __future__ import annotations

import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter


def render(size: int) -> bytes:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    m = size * 0.04
    rect = QRectF(m, m, size - 2 * m, size - 2 * m)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#316ac5"))
    p.drawRoundedRect(rect, size * 0.18, size * 0.18)
    p.setPen(QColor("#ffffff"))
    font = QFont("Arial", weight=QFont.Weight.Bold)
    font.setPixelSize(int(size * 0.42))
    p.setFont(font)
    p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "IMS")
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
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
    os.makedirs(out, exist_ok=True)
    pngs = {s: render(s) for s in (16, 32, 48, 128, 256, 512)}
    with open(os.path.join(out, "ims.png"), "wb") as f:
        f.write(pngs[256])
    write_ico(os.path.join(out, "ims.ico"), {s: pngs[s] for s in (16, 32, 48, 256)})
    write_icns(os.path.join(out, "ims.icns"), pngs)
    print(f"Icons written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
