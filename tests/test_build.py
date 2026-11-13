"""scripts/build.py on a hand-written source sample. No network."""
import copy
import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import build  # noqa: E402

SOURCE = json.loads((HERE / 'fixtures/source.json').read_text(encoding='utf-8'))
TODAY = '2026-11-20'
NOW = datetime.datetime(2026, 11, 20, 8, 23, tzinfo=build.TAIPEI)


def run(source, data_dir, today=TODAY, now=NOW):
    rows, codes = build.published_state(data_dir)
    records, errors = build.validate(source, today, rows)
    if errors:
        return errors, None
    return [], build.publish(data_dir, build.render(records), build.build_meta(records, 'sha', now))


class Output(unittest.TestCase):
    def test_files_match_expected_byte_for_byte(self):
        records, errors = build.validate(SOURCE, TODAY, 0)
        self.assertEqual(errors, [])
        files = build.render(records)
        expected = {p.stem: p.read_text(encoding='utf-8') for p in (HERE / 'fixtures/expected').glob('*.json')}
        self.assertEqual(files, expected)

    def test_output_is_valid_json(self):
        records, _ = build.validate(SOURCE, TODAY, 0)
        for text in build.render(records).values():
            json.loads(text)

    def test_source_order_does_not_matter(self):
        a, _ = build.validate(SOURCE, TODAY, 0)
        b, _ = build.validate(list(reversed(SOURCE)), TODAY, 0)
        self.assertEqual(build.render(a), build.render(b))

    def test_meta(self):
        records, _ = build.validate(SOURCE, TODAY, 0)
        meta = build.build_meta(records, 'abc', NOW)
        self.assertEqual(meta, {
            'schemaVersion': 1,
            'source': build.SOURCE_URL,
            'sourceSha256': 'abc',
            'firstSeenAt': '2026-11-20T08:23:00+08:00',
            'dates': {
                '2026-11-20': {'rows': 5, 'freeSeats': 81},
                '2026-11-21': {'rows': 1, 'freeSeats': 7},
            },
        })


class Publish(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / 'data'

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_run_writes_days_and_meta(self):
        errors, changed = run(SOURCE, self.data)
        self.assertEqual(errors, [])
        self.assertTrue(changed)
        self.assertEqual(sorted(p.name for p in self.data.iterdir()), ['2026-11-20.json', '2026-11-21.json', 'meta.json'])

    def test_same_source_changes_nothing_not_even_meta(self):
        run(SOURCE, self.data)
        meta_before = (self.data / 'meta.json').read_text()
        later = NOW + datetime.timedelta(hours=6)
        errors, changed = run(SOURCE, self.data, now=later)
        self.assertEqual(errors, [])
        self.assertFalse(changed)
        self.assertEqual((self.data / 'meta.json').read_text(), meta_before)

    def test_day_missing_from_source_is_deleted(self):
        run(SOURCE, self.data)
        source = [r for r in SOURCE if r['trnOpDate'] != '2026-11-21']
        errors, changed = run(source, self.data)
        self.assertTrue(changed)
        self.assertFalse((self.data / '2026-11-21.json').exists())
        meta = json.loads((self.data / 'meta.json').read_text())
        self.assertEqual(list(meta['dates']), ['2026-11-20'])

    def test_seat_change_rewrites_day_and_meta(self):
        run(SOURCE, self.data)
        source = copy.deepcopy(SOURCE)
        source[0]['freeSeats'] = '6'
        errors, changed = run(source, self.data)
        self.assertTrue(changed)
        self.assertIn('"freeSeats":6', (self.data / '2026-11-21.json').read_text())


class Refuse(unittest.TestCase):
    """Broken sources must never reach data/: the mirror would delete the published days."""

    def errors(self, source, published_rows=0):
        return build.validate(source, TODAY, published_rows)[1]

    def test_empty_array(self):
        self.assertTrue(self.errors([]))

    def test_not_an_array(self):
        self.assertTrue(self.errors({'error': 'x'}))

    def test_missing_field(self):
        source = copy.deepcopy(SOURCE)
        del source[1]['freeSeats']
        self.assertTrue(self.errors(source))

    def test_bad_values(self):
        for field, value in [('freeSeats', '-1'), ('freeSeats', 'abc'), ('freeSeats', True), ('trnNo', '1A'),
                             ('seatOriStaCode', '100'), ('trnOpDate', '2026/11/20'), ('trnOpDate', '2026-02-30')]:
            source = copy.deepcopy(SOURCE)
            source[1][field] = value
            self.assertTrue(self.errors(source), (field, value))

    def test_duplicate_combination(self):
        self.assertTrue(self.errors(SOURCE + [dict(SOURCE[1], freeSeats='3')]))

    def test_today_missing(self):
        self.assertTrue(build.validate(SOURCE, '2026-11-19', 0)[1])

    def test_less_than_half_of_published(self):
        self.assertTrue(self.errors(SOURCE, published_rows=13))
        self.assertEqual(self.errors(SOURCE, published_rows=12), [])

    def test_refused_run_leaves_data_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'data'
            run(SOURCE, data)
            before = {p.name: p.read_text() for p in data.iterdir()}
            errors, _ = run(SOURCE[:1], data)  # 1 row vs 6 published
            self.assertTrue(errors)
            self.assertEqual({p.name: p.read_text() for p in data.iterdir()}, before)


class Drift(unittest.TestCase):
    def test_zero_seats_publishes_but_warns(self):
        source = copy.deepcopy(SOURCE)
        source[1]['freeSeats'] = '0'
        records, errors = build.validate(source, TODAY, 0)
        self.assertEqual(errors, [])
        self.assertTrue(build.drift(source, records, set()))

    def test_new_station_code(self):
        records, _ = build.validate(SOURCE, TODAY, 0)
        self.assertEqual(build.drift(SOURCE, records, {'1000', '3300', '3360', '4400', '7000'}), [])
        self.assertTrue(build.drift(SOURCE, records, {'1000', '3300', '3360', '4400'}))

    def test_first_run_has_nothing_to_compare_codes_with(self):
        records, _ = build.validate(SOURCE, TODAY, 0)
        self.assertEqual(build.drift(SOURCE, records, set()), [])

    def test_new_field_is_dropped_and_warned(self):
        source = copy.deepcopy(SOURCE)
        source[1]['carClass'] = '1100'
        records, errors = build.validate(source, TODAY, 0)
        self.assertEqual(errors, [])
        self.assertNotIn('carClass', build.render(records)['2026-11-20'])
        self.assertTrue(build.drift(source, records, set()))


if __name__ == '__main__':
    unittest.main()
