#!/usr/bin/env bash
# Builds the Linux artifacts: a portable tar.gz and a .deb installer, both with
# the embedded PostgreSQL. Data persists in ~/.local/share/IMS.
#   packaging/linux/build.sh [version]
set -euo pipefail

VERSION="${1:-0.0.0}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
if [ -x venv/bin/python ]; then PY=venv/bin/python; fi
"$PY" -m pip install -q -r requirements.txt pyinstaller

"$PY" packaging/fetch_postgres.py
"$PY" packaging/make_icon.py
"$PY" -m PyInstaller --noconfirm --clean --distpath packaging/dist packaging/ims.spec

OUT="packaging/linux/output"
rm -rf "$OUT" && mkdir -p "$OUT"

tar -C packaging/dist -czf "$OUT/ims-$VERSION-linux-x64.tar.gz" ims

# .deb: app in /opt/ims, launcher symlink, desktop entry + icon.
STAGE="$OUT/deb"
mkdir -p "$STAGE/DEBIAN" "$STAGE/opt" "$STAGE/usr/bin" \
         "$STAGE/usr/share/applications" "$STAGE/usr/share/icons/hicolor/256x256/apps"
cp -a packaging/dist/ims "$STAGE/opt/ims"
ln -s /opt/ims/ims "$STAGE/usr/bin/ims"
cp packaging/icons/ims.png "$STAGE/usr/share/icons/hicolor/256x256/apps/ims.png"
cat > "$STAGE/usr/share/applications/ims.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=IMS
Comment=Inventory Management System
Exec=/opt/ims/ims
Icon=ims
Categories=Office;
EOF
cat > "$STAGE/DEBIAN/control" <<EOF
Package: ims
Version: $VERSION
Architecture: amd64
Maintainer: Glascutr <nazmul@glascutr.com>
Depends: libc6, libxcb-cursor0
Description: Inventory Management System
 Desktop inventory management application with an embedded PostgreSQL
 database. User data is stored per-user in ~/.local/share/IMS and is
 never removed by package upgrades or removal.
EOF
dpkg-deb --build --root-owner-group "$STAGE" "$OUT/ims_${VERSION}_amd64.deb"
rm -rf "$STAGE"

echo "Artifacts in $OUT:"
ls -lh "$OUT"
