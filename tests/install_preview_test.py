#!/usr/bin/env python3
"""Package deployment tests; no compiler, account or Windows installation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_preview", ROOT / "tools/packaging/install_preview.py")
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewInstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="venture-preview-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.layout = self.base / "package"
        self.destination = self.base / "preview"
        self.package(b"first")

    def package(self, payload):
        self.layout.mkdir(exist_ok=True)
        for name in ("venture.exe", "venture-runtime.exe", "venture-passthrough.cmd"):
            (self.layout / name).write_bytes(payload + name.encode())
        files = {p.name: {"bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in self.layout.iterdir() if p.name != "release-files.json"}
        (self.layout / "release-files.json").write_text(json.dumps({"files": files}))

    def test_install_reuse_and_update_preserve_previous_build(self):
        first = preview.install(self.layout, self.destination, "revision-one")
        self.assertEqual(preview.install(self.layout, self.destination, "revision-one")["directory"], first["directory"])
        self.assertEqual(len(list((self.destination / "versions").iterdir())), 1)
        first_bytes = (Path(first["directory"]) / "venture.exe").read_bytes()
        self.package(b"second")
        second = preview.install(self.layout, self.destination, "revision-two")
        self.assertNotEqual(first["directory"], second["directory"])
        self.assertEqual(second["previous_version"], first["version"])
        self.assertEqual((Path(first["directory"]) / "venture.exe").read_bytes(), first_bytes)
        self.assertEqual(json.loads((self.destination / "current.json").read_text()), second)

    def test_invalid_package_never_creates_an_installation(self):
        (self.layout / "venture.exe").write_bytes(b"changed")
        with self.assertRaises(RuntimeError):
            preview.install(self.layout, self.destination, "invalid")
        self.assertFalse(self.destination.exists())

    def test_copy_failure_keeps_current_build(self):
        first = preview.install(self.layout, self.destination, "first")
        current = (self.destination / "current.json").read_bytes()
        self.package(b"second")
        with patch.object(preview.shutil, "copytree", side_effect=OSError("copy failed")):
            with self.assertRaises(OSError):
                preview.install(self.layout, self.destination, "second")
        self.assertEqual((self.destination / "current.json").read_bytes(), current)
        self.assertTrue(Path(first["directory"]).is_dir())
        self.assertEqual(len(list((self.destination / "versions").iterdir())), 1)

    def test_changed_copy_is_not_published(self):
        first = preview.install(self.layout, self.destination, "first")
        self.package(b"second")
        copy = preview.shutil.copytree
        def corrupt(source, target):
            copy(source, target)
            (target / "venture.exe").write_bytes(b"incomplete transfer")
        with patch.object(preview.shutil, "copytree", side_effect=corrupt):
            with self.assertRaises(RuntimeError):
                preview.install(self.layout, self.destination, "second")
        self.assertEqual(json.loads((self.destination / "current.json").read_text())["directory"], first["directory"])

    def test_unowned_directory_is_not_modified(self):
        self.destination.mkdir()
        (self.destination / "personal.txt").write_text("keep")
        with self.assertRaises(RuntimeError):
            preview.install(self.layout, self.destination, "first")
        self.assertEqual(list(self.destination.iterdir()), [self.destination / "personal.txt"])

    def test_modified_installed_files_are_not_overwritten(self):
        first = preview.install(self.layout, self.destination, "first")
        executable = Path(first["directory"]) / "venture.exe"
        executable.write_bytes(b"user modification")
        with self.assertRaises(RuntimeError):
            preview.install(self.layout, self.destination, "first")
        self.assertEqual(executable.read_bytes(), b"user modification")

    def test_linked_destination_is_rejected(self):
        real = self.base / "real"
        real.mkdir()
        try:
            self.destination.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest("Directory links are unavailable")
        with self.assertRaises(RuntimeError):
            preview.install(self.layout, self.destination, "first")
        self.assertEqual(list(real.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
