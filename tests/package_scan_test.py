#!/usr/bin/env python3
"""Shipping scanner regression tests and a check of the actual built launcher."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import package_release as release


class PackageScanTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="venture-package-scan-")
        self.addCleanup(temporary.cleanup)
        self.layout = Path(temporary.name)
        self.payload = self.layout / "venture.exe"

    def scan(self, forbidden=()):
        release.scan(self.layout, forbidden, ["McFredward"], ["MCBEAST"])

    def test_public_info_link_is_not_the_build_account_in_ascii_and_both_utf16_alignments(self):
        for encoding in ("utf-8", "utf-16le"):
            for prefix in (b"", b"x"):
                with self.subTest(encoding=encoding, prefix=prefix):
                    self.payload.write_bytes(prefix + (release.PUBLIC_PROJECT_URL + "\0").encode(encoding))
                    self.scan()

    def test_public_link_does_not_hide_private_paths_or_identities_in_the_same_file(self):
        for encoding in ("utf-8", "utf-16le"):
            for value in (r"C:\Users\McFredward\private", "/srv/McFredward/private",
                          r"CORP\McFredward", "McFredward@host", "built on MCBEAST.",
                          "D:/projects/Venture/private", "/home/other/source.cpp"):
                with self.subTest(encoding=encoding, value=value):
                    self.payload.write_bytes((release.PUBLIC_PROJECT_URL + "\0" + value).encode(encoding))
                    with self.assertRaisesRegex(RuntimeError, "Non-redistributable"):
                        self.scan(["D:/projects/Venture"])

    def test_unknown_urls_and_extended_paths_keep_the_account_check(self):
        for value in ("https://example.org/McFredward/private",
                      "https://github.com/McFredward/other-project",
                      release.PUBLIC_PROJECT_URL + "/private",
                      release.PUBLIC_PROJECT_URL + "?login=McFredward"):
            with self.subTest(value=value):
                self.payload.write_bytes(value.encode())
                with self.assertRaisesRegex(RuntimeError, "Non-redistributable"):
                    self.scan()

    def test_explicit_forbidden_content_still_wins_over_public_identity_exception(self):
        self.payload.write_bytes(release.PUBLIC_PROJECT_URL.encode())
        with self.assertRaisesRegex(RuntimeError, "Non-redistributable"):
            self.scan([release.PUBLIC_PROJECT_URL])

    def test_public_and_private_links_inside_compressed_jar_entries(self):
        archive = self.layout / "framework.jar"
        for value, allowed in ((release.PUBLIC_PROJECT_URL, True),
                               (release.PUBLIC_PROJECT_URL + "\0CORP\\McFredward", False)):
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as jar:
                jar.writestr("reference", value)
            if allowed:
                self.scan()
            else:
                with self.assertRaisesRegex(RuntimeError, "Non-redistributable"):
                    self.scan()


def check_launcher(binary: Path, strip: str):
    # Use the same strip/remap/scan sequence as the release packager. Force the
    # reported account even on CI runners with unrelated account names.
    with tempfile.TemporaryDirectory(prefix="venture-launcher-release-scan-") as temporary:
        layout = Path(temporary)
        target = layout / binary.name
        shutil.copy2(binary, target)
        subprocess.run([strip, "--strip-all", str(target)], check=True)
        if target.suffix.lower() == ".exe":
            release.remap_pe_source_names(target)
        data = target.read_bytes()
        assert any(release.PUBLIC_PROJECT_URL.encode(encoding) in data for encoding in ("utf-8", "utf-16le")), \
            "The actual launcher must contain the Steam Frame Info link"
        users = ["McFredward", os.environ.get("USERNAME", ""), os.environ.get("USER", "")]
        hosts = ["MCBEAST", os.environ.get("COMPUTERNAME", "")]
        release.scan(layout, [str(ROOT), str(binary.resolve().parent), str(Path.home())], users, hosts)
    print("PASS release scanner on actual stripped launcher with account McFredward")


if __name__ == "__main__":
    if "--launcher" in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--launcher", type=Path, required=True)
        parser.add_argument("--strip", required=True)
        args = parser.parse_args()
        check_launcher(args.launcher, args.strip)
    else:
        unittest.main()
