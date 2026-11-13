"""The yt-dlp that install.sh downloads is checked before it is put on PATH
(run: python -m unittest discover tests).

install.sh runs as a whole (it installs system packages), so this test takes the yt-dlp part out
of it and runs that with a stand-in `curl`: the script has to accept a good download, and leave
nothing behind when the download is wrong, the checksum list is missing or the fetch fails.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "install.sh"

CURL = """#!/usr/bin/env bash
out=""; url=""
while [ $# -gt 0 ]; do case "$1" in -o) out="$2"; shift 2;; -*) shift;; *) url="$1"; shift;; esac; done
%s
"""

GOOD = ("""( [ "$(basename "$url")" = "SHA2-256SUMS" ] && printf '%s  yt-dlp\\n' "$(printf fake-binary | sha256sum | cut -d' ' -f1)" > "$out" ) """
        """|| printf fake-binary > "$out" """)
WRONG = ("""( [ "$(basename "$url")" = "SHA2-256SUMS" ] && printf '%s  yt-dlp\\n' """
         """"0000000000000000000000000000000000000000000000000000000000000000" > "$out" ) """
         """|| printf fake-binary > "$out" """)
NO_SUMS = """[ "$(basename "$url")" = "SHA2-256SUMS" ] && exit 22; printf fake-binary > "$out" """
FETCH_FAILS = """printf '%s' "404: Not Found" > "$out"; exit 22"""


def ytdlp_part() -> str:
    """install.sh's yt-dlp section: the SHA2-256SUMS download and ensure_ytdlp()."""
    script = INSTALL.read_text()
    start = script.index("YTDLP_RELEASE=")
    end = script.index("# Senada tetap bisa dipasang")
    return script[start:end]


@unittest.skipUnless(shutil.which("bash") and shutil.which("sha256sum"), "needs bash and sha256sum")
class Download(unittest.TestCase):
    def install(self, curl_body: str) -> tuple[int, Path]:
        """Run ensure_ytdlp() with a stand-in curl; (exit code, the ~/.local/bin it used)."""
        tmp = Path(tempfile.mkdtemp())
        (tmp / "bin").mkdir()
        curl = tmp / "bin" / "curl"
        curl.write_text(CURL % curl_body)
        curl.chmod(curl.stat().st_mode | stat.S_IEXEC)
        bindir = tmp / "home" / ".local" / "bin"
        bindir.mkdir(parents=True)
        part = tmp / "ytdlp-part.sh"
        part.write_text(ytdlp_part())
        done = subprocess.run(
            ["bash", "-c",
             'BIN_DIR="$1"; info(){ :; }; ok(){ :; }; warn(){ :; }; err(){ :; }\n'
             'source "$2"\nensure_ytdlp; echo "rc=$?"',
             "x", str(bindir), str(part)],
            env={**os.environ, "PATH": f"{tmp / 'bin'}:{os.environ['PATH']}"},
            capture_output=True, text=True, timeout=60,
        )
        return done, bindir

    def test_a_verified_download_is_installed(self):
        done, bindir = self.install(GOOD)
        self.assertIn("rc=0", done.stdout, done.stderr)
        self.assertTrue(os.access(bindir / "yt-dlp", os.X_OK))
        self.assertEqual(sorted(p.name for p in bindir.iterdir()), ["yt-dlp"])  # no .part/.sums left

    def test_a_download_that_does_not_match_the_checksum_is_dropped(self):
        done, bindir = self.install(WRONG)
        self.assertIn("rc=1", done.stdout, done.stderr)
        self.assertFalse((bindir / "yt-dlp").exists())

    def test_no_checksum_list_means_no_binary(self):
        done, bindir = self.install(NO_SUMS)
        self.assertIn("rc=1", done.stdout, done.stderr)
        self.assertFalse((bindir / "yt-dlp").exists())

    def test_a_failed_fetch_leaves_nothing_behind(self):
        done, bindir = self.install(FETCH_FAILS)
        self.assertIn("rc=1", done.stdout, done.stderr)
        self.assertEqual(list(bindir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
