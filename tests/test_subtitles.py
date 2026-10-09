import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('subtitles', Path(__file__).parents[1] / 'scripts/subtitles.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class SubtitleTests(unittest.TestCase):
    def test_continuation_merges_across_whisper_segments(self):
        raw = [dict(start=0, end=3, text='Scheduled for pending'), dict(start=3, end=3.6, text='termination.')]
        result = m.segment_cues(raw, 'en', 4)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['text'], 'Scheduled for pending termination.')
        self.assertEqual(result[0]['end'], 3.6)

    def test_short_cues_do_not_cross_silence(self):
        cues = [dict(id=1, start=0, end=1, text='Yes.'), dict(id=2, start=4, end=4.2, text='No.')]
        self.assertEqual(len(m.merge_short_cues(cues, 'en')), 2)

    def test_punctuation_and_timing(self):
        words = [dict(start=i*.5, end=(i+1)*.5, word=w) for i,w in enumerate([' Hello', ' world.', ' Next', ' sentence!'])]
        cues = m.segment_cues([dict(words=words)], 'en', 2)
        self.assertEqual([c['text'] for c in cues], ['Hello world.', 'Next sentence!'])
        self.assertEqual(cues[0]['end'], cues[1]['start'])

    def test_platform_font(self):
        for platform, font in [('darwin','PingFang SC'), ('linux','Noto Sans CJK SC'), ('win32','Microsoft YaHei')]:
            with patch.object(m.sys, 'platform', platform):
                self.assertEqual(m.default_font(), font)

    def test_long_line_warns_without_changing_text(self):
        with patch('sys.stderr') as stderr:
            m.warn_layout('中'*23, 'zh', 7)
            self.assertTrue(stderr.write.called)

if __name__ == '__main__':
    unittest.main()
