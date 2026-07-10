"""Download portable PostgreSQL binaries into packaging/pgsql for bundling.

Uses https://github.com/theseus-rs/postgresql-binaries (self-contained bin/lib/share
builds for Windows, macOS and Linux). Run before `pyinstaller ims.spec`; the spec
bundles packaging/pgsql/ if it exists. Keeps only the tools the app needs.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import tarfile
import urllib.request

PG_VERSION = "17.2.0"

TARGETS = {
    ("win32", "AMD64"): "x86_64-pc-windows-msvc",
    ("linux", "x86_64"): "x86_64-unknown-linux-gnu",
    ("linux", "aarch64"): "aarch64-unknown-linux-gnu",
    ("darwin", "arm64"): "aarch64-apple-darwin",
    ("darwin", "x86_64"): "x86_64-apple-darwin",
}

KEEP_TOOLS = {"postgres", "initdb", "pg_ctl", "psql", "pg_dump", "pg_restore",
              "pg_isready"}


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "pgsql")
    if os.path.isdir(dest):
        print(f"{dest} already exists, skipping download")
        return 0

    key = (sys.platform, platform.machine())
    target = TARGETS.get(key)
    if not target:
        print(f"No PostgreSQL binaries mapping for {key}", file=sys.stderr)
        return 1

    name = f"postgresql-{PG_VERSION}-{target}"
    url = (f"https://github.com/theseus-rs/postgresql-binaries/releases/"
           f"download/{PG_VERSION}/{name}.tar.gz")
    archive = os.path.join(here, f"{name}.tar.gz")
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, archive)

    print("Extracting...")
    with tarfile.open(archive) as tf:
        try:
            tf.extractall(here, filter="tar")
        except TypeError:  # Python < 3.12
            tf.extractall(here)
    os.remove(archive)
    extracted = os.path.join(here, name)
    if not os.path.isdir(extracted):  # some releases nest under the version number
        extracted = os.path.join(here, PG_VERSION)
    os.rename(extracted, dest)

    # Trim what the app never uses.
    for sub in ("include", "doc", os.path.join("share", "doc"),
                os.path.join("share", "man")):
        shutil.rmtree(os.path.join(dest, sub), ignore_errors=True)
    bin_dir = os.path.join(dest, "bin")
    for f in os.listdir(bin_dir):
        stem = f[:-4] if f.endswith(".exe") else f
        if "." not in stem and stem not in KEEP_TOOLS:  # keep all .dll/.so helpers
            os.remove(os.path.join(bin_dir, f))
    print(f"PostgreSQL {PG_VERSION} ready in {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
