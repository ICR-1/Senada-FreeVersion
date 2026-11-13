"""Text that comes from the network is shown as text, not as markup
(run: python -m unittest discover tests).

Qt Quick's Label treats a string that looks like HTML as rich text by default. Titles, artist
names and lyrics come from YouTube Music, Spotify and LRCLIB, so a page there could put an
<img src="http://…"> in a title or a lyric line and Senada would fetch it while that line is on
screen. Every label that shows such a string therefore has textFormat: Text.PlainText.
"""

import unittest
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "qml"
PLAIN = "textFormat: Text.PlainText"

# how many plain-text labels each file needs: one per label that shows text from the network
EXPECTED = {
    "LinkLabel.qml": 1,        # artist and album names, everywhere they are linked
    "LyricsView.qml": 1,       # a lyric line (the full-screen player)
    "RightPanel.qml": 1,       # a lyric line (the side panel)
    "Toast.qml": 1,            # messages that carry a title
    "TrackRow.qml": 1,         # track title
    "Card.qml": 2,             # card name and subtitle
    "MatchPicker.qml": 3,      # header, candidate name, candidate line
    "ImmersivePlayer.qml": 2,  # album and track title (the artist is a LinkLabel)
    "MiniPlayer.qml": 2,       # title and artist
    "PlayerBar.qml": 1,        # title (the artist is a LinkLabel)
    "PageHeader.qml": 2,       # page title, plus the description it already had
    "Sidebar.qml": 1,          # playlist name
    "SearchPage.qml": 1,       # name of the result card at the top
    "HomePage.qml": 2,         # the "continue listening" title and artist line
}


class PlainText(unittest.TestCase):
    def test_network_text_is_not_markup(self):
        for name, need in EXPECTED.items():
            with self.subTest(qml=name):
                text = (QML / name).read_text()
                self.assertGreaterEqual(text.count(PLAIN), need,
                                        f"{name} shows text from the network without {PLAIN}")

    def test_lyrics_are_the_reason_it_matters(self):
        # the lyric delegate is the one place where a third party writes whole lines of text
        lyrics = (QML / "LyricsView.qml").read_text()
        self.assertIn('text: modelData.text || "♪"', lyrics)
        line = next(l for l in lyrics.splitlines() if "textFormat" in l)
        self.assertIn(PLAIN, line)


if __name__ == "__main__":
    unittest.main()
