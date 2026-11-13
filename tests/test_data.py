"""Invariants on the published data/ directory. Skipped before the first build."""
import datetime
import json
import unittest
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / 'data'
FIELDS = ['trnOpDate', 'trnNo', 'seatOriStaCode', 'seatDstStaCode', 'freeSeats']
DAYS = sorted(p for p in DATA.glob('*.json') if p.name != 'meta.json') if DATA.exists() else []


@unittest.skipUnless(DAYS, 'no data/ yet')
class Schema(unittest.TestCase):
    def test_only_day_files_and_meta(self):
        names = {p.name for p in DATA.iterdir()}
        self.assertIn('meta.json', names)
        for n in names - {'meta.json'}:
            self.assertRegex(n, r'^\d{4}-\d\d-\d\d\.json$')

    def test_day_files(self):
        for p in DAYS:
            text = p.read_text(encoding='utf-8')
            rows = json.loads(text)
            self.assertTrue(rows, p.name)
            lines = text.split('\n')
            self.assertEqual((lines[0], lines[-2], lines[-1]), ('[', ']', ''), p.name)
            self.assertEqual(len(lines), len(rows) + 3, f'{p.name}: one record per line')
            keys = []
            for r in rows:
                self.assertEqual(list(r), FIELDS, p.name)
                self.assertEqual(r['trnOpDate'], p.stem)
                self.assertRegex(r['trnNo'], r'^\d+$')
                self.assertRegex(r['seatOriStaCode'], r'^\d{4}$')
                self.assertRegex(r['seatDstStaCode'], r'^\d{4}$')
                self.assertIs(type(r['freeSeats']), int)
                self.assertGreaterEqual(r['freeSeats'], 0)
                keys.append((int(r['trnNo']), r['seatOriStaCode'], r['seatDstStaCode']))
            self.assertEqual(keys, sorted(keys), f'{p.name}: sorted')
            self.assertEqual(len(keys), len(set(keys)), f'{p.name}: unique')

    def test_meta_matches_files(self):
        meta = json.loads((DATA / 'meta.json').read_text(encoding='utf-8'))
        self.assertEqual(list(meta), ['schemaVersion', 'source', 'sourceSha256', 'firstSeenAt', 'dates'])
        self.assertEqual(meta['schemaVersion'], 1)
        self.assertRegex(meta['sourceSha256'], r'^[0-9a-f]{64}$')
        self.assertRegex(meta['firstSeenAt'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+08:00$')
        datetime.datetime.fromisoformat(meta['firstSeenAt'])
        self.assertEqual(list(meta['dates']), [p.stem for p in DAYS])
        for p in DAYS:
            rows = json.loads(p.read_text(encoding='utf-8'))
            self.assertEqual(meta['dates'][p.stem], {'rows': len(rows), 'freeSeats': sum(r['freeSeats'] for r in rows)})


if __name__ == '__main__':
    unittest.main()
