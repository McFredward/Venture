# Optional preview package deployment

The Python helpers accept an ordinary Windows Venture release layout containing
`release-files.json`, `venture.exe` and `venture-runtime.exe`. They require no
passthrough starter, passthrough runtime or build/install script.

```powershell
python tools/packaging/install_preview.py --layout dist/Venture-win64 --install-root D:/Apps/Venture-Preview --revision REVISION
```

The installer verifies manifest paths and file hashes before claiming a new
installation, updates one fixed directory, repairs interrupted copies and removes
only previously managed obsolete files. It refuses linked destinations and
unknown installation ownership. Its historical preview-owner identifiers remain
for migration compatibility; they do not restrict the installed application to MR.
Recognized old version directories are removed; unknown content is retained.

`clean_preview_package.py` removes only the fixed generated
`dist/Venture-win64` layout, including an interrupted package without a manifest.
It refuses links and junctions. It is optional and is not used by the independent
Windows build/install scripts, which package into their own temporary output.

Run `python tests/install_preview_test.py` and
`python tests/preview_package_test.py` for actual filesystem checks. Windows also
checks the behavior of locked executable targets.
