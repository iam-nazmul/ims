#!/usr/bin/env bash
# Builds IMS.app and a .dmg on macOS (run on a Mac; ad-hoc codesigned).
# Data persists in ~/Library/Application Support/IMS.
#   packaging/macos/build.sh [version]
set -euo pipefail

VERSION="${1:-0.0.0}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
"$PY" -m pip install -q -r requirements.txt pyinstaller

"$PY" packaging/fetch_postgres.py
"$PY" packaging/make_icon.py
"$PY" -m PyInstaller --noconfirm --clean --distpath packaging/dist packaging/ims.spec

codesign --force --deep -s - packaging/dist/IMS.app

OUT="packaging/macos/output"
rm -rf "$OUT" && mkdir -p "$OUT"
STAGE="$OUT/dmg"
mkdir -p "$STAGE"
cp -R packaging/dist/IMS.app "$STAGE/"
ln -s /Applications "$STAGE/Applications"
ARCH="$(uname -m)"
hdiutil create -volname "IMS" -srcfolder "$STAGE" -ov -format UDZO \
        "$OUT/ims-$VERSION-macos-$ARCH.dmg"
rm -rf "$STAGE"

echo "Artifacts in $OUT:"
ls -lh "$OUT"
