"""mpv's IPC socket stays in a directory only this user can use
(run: python -m unittest discover tests)."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QCoreApplication

from senada.engine import AudioEngine, ipc_endpoint

APP = QCoreApplication.instance() or QCoreApplication([])


def without_runtime_dir():
    """XDG_RUNTIME_DIR unset, as in a cron job or a bare ssh session."""
    environ = {k: v for k, v in os.environ.items() if k != "XDG_RUNTIME_DIR"}
    return mock.patch.dict(os.environ, environ, clear=True)


class Endpoint(unittest.TestCase):
    def test_private_directory_without_a_runtime_dir(self):
        with without_runtime_dir():
            path, private = ipc_endpoint(1234)
            try:
                self.assertIsNotNone(private, "the socket would land in the shared temp directory")
                self.assertEqual(path, os.path.join(private, "senada-mpv-1234.sock"))
                self.assertEqual(stat.S_IMODE(os.stat(private).st_mode), 0o700)
                self.assertNotEqual(os.path.dirname(path), tempfile.gettempdir())
                self.assertLess(len(path), 100, "Unix socket paths are limited to about 108 characters")
            finally:
                os.rmdir(private)

    def test_runtime_dir_is_used_as_it_is(self):
        with tempfile.TemporaryDirectory() as runtime:
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": runtime}):
                path, private = ipc_endpoint(7)
                self.assertIsNone(private, "nothing extra to clean up")
                self.assertEqual(path, os.path.join(runtime, "senada-mpv-7.sock"))

    def test_a_runtime_dir_that_does_not_exist_is_not_used(self):
        with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": "/nonexistent/senada-test"}):
            path, private = ipc_endpoint(9)
            try:
                self.assertIsNotNone(private)
                self.assertTrue(os.path.isdir(private))
                self.assertTrue(path.startswith(private))
            finally:
                os.rmdir(private)


class Engine(unittest.TestCase):
    def make(self):
        with mock.patch.object(AudioEngine, "_start_mpv"), mock.patch("atexit.register"):
            return AudioEngine()

    def test_the_engine_uses_the_endpoint_and_cleans_up_after_itself(self):
        with without_runtime_dir():
            engine = self.make()
            private = engine._private_dir
            self.assertIsNotNone(private)
            Path(engine.ipc_path).write_text("stand-in for mpv's socket")
            engine.quit()
            self.assertFalse(os.path.exists(private), "the private directory stayed behind")

    def test_quit_is_harmless_without_a_private_directory(self):
        with tempfile.TemporaryDirectory() as runtime:
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": runtime}):
                engine = self.make()
                engine.quit()
                self.assertEqual(os.listdir(runtime), [], "the desktop runtime dir was touched")


if __name__ == "__main__":
    unittest.main()
