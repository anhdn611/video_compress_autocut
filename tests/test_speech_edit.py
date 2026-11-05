import unittest
from speech_edit import normalize_transcript, refinement_ranges, repeat_candidates, map_draft_ranges


class SpeechEditTests(unittest.TestCase):
    def setUp(self):
        self.units = [dict(id='a', start=1., end=3., text='Hôm nay tôi giới thiệu sản phẩm này.', needs_review=False),
                      dict(id='b', start=4., end=6., text='Hôm nay tôi giới thiệu sản phẩm này.', needs_review=False),
                      dict(id='c', start=7., end=9., text='Giá là một trăm nghìn đồng.', needs_review=False)]
        self.t = dict(units=self.units)
        self.d = [dict(remove_ids=['a'], replacement_ids=['b'], reason_type='duplicate', reason='Câu a nói lại đầy đủ ở câu b.')]

    def test_removes_only_grounded_units_and_keeps_rest(self):
        self.assertEqual(refinement_ranges(self.t, self.d, 10), [[3.5, 10]])
        self.assertTrue(repeat_candidates(self.units))

    def test_never_remove_low_confidence_or_invented_ids(self):
        self.units[0]['needs_review'] = True
        with self.assertRaisesRegex(ValueError, 'uncertain_recognition'):
            refinement_ranges(self.t, self.d, 10)
        self.units[0]['needs_review'] = False
        self.d[0]['remove_ids'] = ['invented']
        with self.assertRaisesRegex(ValueError, 'unknown_transcript_id'):
            refinement_ranges(self.t, self.d, 10)

    def test_replacement_must_survive(self):
        self.d[0]['remove_ids'] = ['a', 'b']
        with self.assertRaisesRegex(ValueError, 'replacement_is_also_removed'):
            refinement_ranges(self.t, self.d, 10)

    def test_complete_deletion_rejected(self):
        self.d = [dict(remove_ids=['a', 'b', 'c'], reason_type='false_start', reason='Bỏ toàn bộ là không hợp lệ.')]
        with self.assertRaisesRegex(ValueError, 'cannot_remove_all_speech'):
            refinement_ranges(self.t, self.d, 10)

    def test_token_times_split_phrases_without_guessing_times(self):
        raw = {'transcription': [dict(text='Xin chào, cảm ơn.', offsets={'from': 0, 'to': 3000},
            tokens=[dict(text='Xin chào,', p=.9, offsets={'from': 100, 'to': 1200}),
                    dict(text=' cảm ơn.', p=.9, offsets={'from': 1500, 'to': 2700})])]}
        units = normalize_transcript(raw, 3)
        self.assertEqual([(u['start'], u['end']) for u in units], [(.1, 1.2), (1.5, 2.7)])

    def test_draft_mapping_crosses_preliminary_cut_without_inventing_time(self):
        self.assertEqual(map_draft_ranges([[1, 5]], [[2, 5], [10, 14]]), [[3, 5], [10, 12]])
        self.assertEqual(map_draft_ranges([[0, 7]], [[2, 5], [10, 14]]), [[2, 5], [10, 14]])

    def test_normalization_converts_milliseconds_and_clamps(self):
        raw = {'transcription': [dict(text=' Xin chào ', offsets={'from': 100, 'to': 1200}, tokens=[dict(text=' Xin', p=.9)])]}
        u = normalize_transcript(raw, 1)[0]
        self.assertEqual((u['start'], u['end']), (.1, 1))
        self.assertFalse(u['needs_review'])


if __name__ == '__main__':
    unittest.main()
