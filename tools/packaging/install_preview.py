#!/usr/bin/env python3
"""Install a verified portable build in an owned, immutable preview directory."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent / "windows"))
from build_installer import load_layout

OWNER = "Venture Steam Link Passthrough preview"
MARKER = "venture-preview-install.json"


def reject_links(path: Path, tree: bool = False) -> None:
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
            raise RuntimeError("Preview paths must not contain links: " + str(candidate))
    if tree and path.exists():
        for directory, directories, files in os.walk(path, followlinks=False):
            for name in directories + files:
                candidate = Path(directory) / name
                if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
                    raise RuntimeError("Preview layout must not contain links: " + str(candidate))


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install(layout: Path, root: Path, revision: str) -> dict:
    # Validate before creating or modifying an installation. Paths are absolute
    # without resolving links away, so redirected destinations are detected.
    layout, root = Path(os.path.abspath(layout)), Path(os.path.abspath(root))
    reject_links(layout, tree=True)
    reject_links(root)
    if root == root.parent or root.is_relative_to(layout) or layout.is_relative_to(root):
        raise RuntimeError("Choose a separate preview installation directory")
    names = load_layout(layout)
    if "venture-passthrough.cmd" not in names:
        raise RuntimeError("The package lacks its passthrough starter")
    manifest_hash = hashlib.sha256((layout / "release-files.json").read_bytes()).hexdigest()
    marker = root / MARKER
    reject_links(marker)
    if root.exists():
        if not marker.is_file() or json.loads(marker.read_text()).get("owner") != OWNER:
            raise RuntimeError("Destination is not an owned Venture preview; choose a new directory")
    else:
        root.mkdir(parents=True)
        write_json(marker, {"owner": OWNER, "schema": 1})
    versions = root / "versions"
    reject_links(versions)
    versions.mkdir(exist_ok=True)
    version = manifest_hash[:24]
    destination = versions / version
    reject_links(destination, tree=True)
    if destination.exists():
        load_layout(destination)  # Never overwrite a modified prior installation.
        if (destination / "release-files.json").read_bytes() != (layout / "release-files.json").read_bytes():
            raise RuntimeError("Installed preview manifest differs")
    else:
        # Same-volume rename publishes the complete image only after verifying
        # all copied bytes. A failed build/copy cannot replace the last build.
        with tempfile.TemporaryDirectory(prefix=".stage-", dir=versions) as temporary:
            staged = Path(temporary) / "image"
            shutil.copytree(layout, staged)
            reject_links(staged, tree=True)
            load_layout(staged)
            if hashlib.sha256((staged / "release-files.json").read_bytes()).hexdigest() != manifest_hash:
                raise RuntimeError("Package changed while installing")
            try:
                staged.rename(destination)
            except OSError:
                if not destination.is_dir():
                    raise
                load_layout(destination)
                if (destination / "release-files.json").read_bytes() != (layout / "release-files.json").read_bytes():
                    raise RuntimeError("Concurrent installation published different content")
    current = root / "current.json"
    reject_links(current)
    previous = json.loads(current.read_text()) if current.exists() else {}
    if previous and previous.get("owner") != OWNER:
        raise RuntimeError("The current preview receipt has a different owner")
    receipt = {"owner": OWNER, "schema": 1, "revision": revision,
               "version": version, "directory": str(destination), "manifest_sha256": manifest_hash}
    if previous.get("version") and previous["version"] != version:
        receipt["previous_version"] = previous["version"]
    write_json(current, receipt)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--install-root", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.layout, args.install_root, args.revision)))


if __name__ == "__main__":
    main()
