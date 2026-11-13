"""A damaged library.json must not stop Senada from starting
(run: python -m unittest discover tests)."""

import json
import tempfile
import unittest
from pathlib import Path

from senada.store import LocalStore


class Damaged(unittest.TestCase):
    def store(self, data):
        path = Path(tempfile.mkdtemp()) / "library.json"
        path.write_text(json.dumps(data))
        return LocalStore(path)

    def test_values_of_the_wrong_shape_are_ignored(self):
        s = self.store({"liked": "x", "playlists": {"a": 1}, "saved": [None, 3], "history": [{"no": "uri"}]})
        self.assertEqual(s.liked(), [])
        self.assertEqual(s.playlists(), [])
        self.assertEqual(s.saved(), [])
        self.assertEqual(s.history(), [])

    def test_a_playlist_without_its_track_list_still_opens(self):
        s = self.store({"playlists": [{"id": "local-1", "name": "Mix"}, {"id": "", "name": "?"}, {"name": "no id"}]})
        self.assertEqual([p["id"] for p in s.playlists()], ["local-1"])
        self.assertEqual(s.playlists()[0]["count"], 0)
        self.assertEqual(s.playlist("local-1")["tracks"], [])

    def test_a_playlist_without_a_name_gets_one(self):
        s = self.store({"playlists": [{"id": "local-1", "tracks": [{"uri": "yt:track:a"}]}]})
        self.assertTrue(s.playlists()[0]["name"])

    def test_tracks_of_the_wrong_shape_are_dropped(self):
        s = self.store({"playlists": [{"id": "local-1", "name": "Mix",
                                       "tracks": [{"uri": "yt:track:a"}, "junk", {"name": "no uri"}]}]})
        self.assertEqual([t["uri"] for t in s.playlist("local-1")["tracks"]], ["yt:track:a"])

    def test_good_data_is_kept_as_it_was(self):
        liked = [{"uri": "yt:track:a", "name": "A", "addedAt": 1}]
        playlist = {"id": "local-1", "name": "Mix", "source": "https://…", "tracks": [{"uri": "yt:track:b"}]}
        s = self.store({"liked": liked, "playlists": [playlist]})
        self.assertEqual(s.liked(), liked)  # addedAt and the like survive
        self.assertEqual(s.playlist("local-1"), playlist)

    def test_a_repaired_library_can_still_be_used(self):
        s = self.store({"playlists": [{"id": "local-1"}]})
        pid = s.create_playlist("Baru", [{"uri": "yt:track:a", "name": "A"}])
        self.assertEqual(s.playlist(pid)["tracks"][0]["uri"], "yt:track:a")
        self.assertEqual([p["id"] for p in s.playlists()], [pid, "local-1"])


if __name__ == "__main__":
    unittest.main()
