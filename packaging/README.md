# packaging/ — installers for Windows, Linux and macOS

Each installer bundles the app (PyInstaller) **and a private PostgreSQL server**
(from [theseus-rs/postgresql-binaries](https://github.com/theseus-rs/postgresql-binaries)),
so end users install nothing else. On first launch `ims/bootstrap.py` runs
`initdb` into the per-user data directory, starts the server on
`127.0.0.1:5455` (override with `IMS_PG_PORT`), loads `db_schema.sql` and sets
`IMS_DATABASE_URL`. The server is stopped again when the app exits.

**Data always persists.** The cluster lives outside the install dir —
`%LOCALAPPDATA%\IMS\pgdata` / `~/.local/share/IMS/pgdata` /
`~/Library/Application Support/IMS/pgdata` — and no installer, upgrade or
uninstall step ever writes there. Product images go next to it under
`IMS/media/`. Delete that folder manually only if you really want a factory reset.

## Building

CI does all three: pushing a tag like `v1.2.0` runs
[.github/workflows/build.yml](../.github/workflows/build.yml) and attaches the
installers to the GitHub release. `workflow_dispatch` builds downloadable
artifacts without a release.

Locally (each script installs deps, downloads PostgreSQL into `packaging/pgsql/`,
generates icons, runs PyInstaller, then packages):

| OS | Command | Output |
|---|---|---|
| Windows | `powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Version 1.0.0` (needs Inno Setup 6) | `packaging/windows/output/ims-setup-*.exe` |
| Linux | `packaging/linux/build.sh 1.0.0` | `packaging/linux/output/*.deb` + `*.tar.gz` |
| macOS | `packaging/macos/build.sh 1.0.0` | `packaging/macos/output/*.dmg` |

Windows/macOS artifacts must be built on that OS (no cross-compiling); iOS is
not a possible target for this stack.

## Files

| File | Purpose |
|---|---|
| `launcher.py` | PyInstaller entry point (`python -m ims` equivalent) |
| `ims.spec` | PyInstaller spec: bundles `db_schema.sql`, `media/`, `pgsql/`; builds `IMS.app` on macOS |
| `fetch_postgres.py` | Downloads + trims portable PostgreSQL for the current platform into `pgsql/` |
| `make_icon.py` | Renders `icons/ims.png` / `.ico` / `.icns` with Qt (no extra deps) |
| `windows/installer.iss` | Inno Setup script; per-user install, stops the DB server before upgrade/uninstall, never touches the data dir |
| `linux/build.sh`, `macos/build.sh` | Platform packaging scripts |

`pgsql/`, `icons/`, `dist/` and `*/output/` are generated and git-ignored.

## Notes

- The embedded server trusts local connections for the `ims` superuser — fine for
  a single-user desktop machine, since only localhost can connect.
- If a dev checkout should use the embedded server instead of a system PostgreSQL,
  set `IMS_PGSQL_DIR=$PWD/packaging/pgsql` before `python -m ims`.
- Upgrading the bundled PostgreSQL major version (see `PG_VERSION` in
  `fetch_postgres.py`) requires a dump/restore of existing user clusters — keep
  the major version stable, or ship migration logic first.
