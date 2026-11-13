"""Turn .cache/seat.json into data/{trnOpDate}.json and data/meta.json.

Refuses to write anything when the source looks broken (see validate). Warnings that should not block publishing
(see drift) go to .cache/drift.txt; the workflow fails on them after the data is pushed.
"""
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = 'https://ods.railway.gov.tw/tra-ods-web/ods/download/dataResource/5a2e672be26f4467a98f121d9ef43885'
SCHEMA_VERSION = 1
FIELDS = ('trnOpDate', 'trnNo', 'seatOriStaCode', 'seatDstStaCode', 'freeSeats')
TAIPEI = datetime.timezone(datetime.timedelta(hours=8))  # no DST in Taiwan
DATE_FILE = re.compile(r'^\d{4}-\d\d-\d\d\.json$')
# A run that would publish less than this share of the rows already published is treated as a broken source.
MIN_ROW_RATIO = 0.5


def normalise(r):
    """Source record (all strings) -> output record, or None if malformed."""
    if not isinstance(r, dict) or not all(k in r for k in FIELDS):
        return None
    d, no, ori, dst, seats = (r[k] for k in FIELDS)
    if not (isinstance(d, str) and re.fullmatch(r'\d{4}-\d\d-\d\d', d)):
        return None
    try:
        datetime.date.fromisoformat(d)
    except ValueError:
        return None
    if not (isinstance(no, str) and re.fullmatch(r'\d+', no)):
        return None
    if not all(isinstance(c, str) and re.fullmatch(r'\d{4}', c) for c in (ori, dst)):
        return None
    if isinstance(seats, str) and re.fullmatch(r'\d+', seats):
        seats = int(seats)
    elif not (type(seats) is int and seats >= 0):
        return None
    return {'trnOpDate': d, 'trnNo': no, 'seatOriStaCode': ori, 'seatDstStaCode': dst, 'freeSeats': seats}


def sort_key(r):
    return int(r['trnNo']), r['seatOriStaCode'], r['seatDstStaCode']


def validate(source, today, published_rows):
    """Return (records, errors). Any error means nothing may be published."""
    if not isinstance(source, list):
        return [], ['source is not a JSON array']
    records, errors, bad = [], [], []
    for i, r in enumerate(source):
        n = normalise(r)
        if n is None:
            bad.append(i)
        else:
            records.append(n)
    if bad:
        errors.append(f'{len(bad)} malformed records, e.g. #{bad[0]}: {json.dumps(source[bad[0]], ensure_ascii=False)[:200]}')
    keys = [(r['trnOpDate'], *sort_key(r)) for r in records]
    if len(keys) != len(set(keys)):
        errors.append(f'{len(keys) - len(set(keys))} duplicate (date, train, from, to) records')
    if today not in {r['trnOpDate'] for r in records}:
        errors.append(f'no records for today ({today})')
    if published_rows and len(records) < published_rows * MIN_ROW_RATIO:
        errors.append(f'{len(records)} records, less than {MIN_ROW_RATIO:.0%} of the {published_rows} already published')
    return records, errors


def drift(source, records, known_codes):
    """Changes that are published anyway but need a look at the README."""
    warnings = []
    extra = {k for r in source if isinstance(r, dict) for k in r} - set(FIELDS)
    if extra:
        warnings.append(f'new source fields (not published): {sorted(extra)}')
    zeros = sum(r['freeSeats'] == 0 for r in records)
    if zeros:
        warnings.append(f'{zeros} records with freeSeats = 0; the README says the source never has them')
    if known_codes:
        new = {r[k] for r in records for k in ('seatOriStaCode', 'seatDstStaCode')} - known_codes
        if new:
            warnings.append(f'station codes not seen before: {sorted(new)}')
    return warnings


def render(records):
    """{date: file text}. One record per line so that git diffs show individual seat changes."""
    by_date = {}
    for r in records:
        by_date.setdefault(r['trnOpDate'], []).append(r)
    out = {}
    for d, rows in by_date.items():
        rows.sort(key=sort_key)
        lines = [json.dumps(r, ensure_ascii=False, separators=(',', ':')) for r in rows]
        out[d] = '[\n' + ',\n'.join(lines) + '\n]\n'
    return out


def build_meta(records, sha256, now):
    dates = {}
    for r in records:
        s = dates.setdefault(r['trnOpDate'], {'rows': 0, 'freeSeats': 0})
        s['rows'] += 1
        s['freeSeats'] += r['freeSeats']
    return {
        'schemaVersion': SCHEMA_VERSION,
        'source': SOURCE_URL,
        'sourceSha256': sha256,
        'firstSeenAt': now.isoformat(timespec='seconds'),
        'dates': dict(sorted(dates.items())),
    }


def publish(data_dir, files, meta):
    """Write the day files, delete days the source no longer has; rewrite meta only if a day file changed.

    Returns True if anything changed.
    """
    data_dir.mkdir(exist_ok=True)
    existing = {p.stem: p for p in data_dir.iterdir() if DATE_FILE.match(p.name)}
    changed = False
    for d, p in existing.items():
        if d not in files:
            p.unlink()
            changed = True
    for d, text in files.items():
        p = data_dir / f'{d}.json'
        if d not in existing or p.read_text(encoding='utf-8') != text:
            p.write_text(text, encoding='utf-8')
            changed = True
    if changed:
        (data_dir / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return changed


def published_state(data_dir):
    """(total rows, station codes) of what is published now; (0, set()) on the first run."""
    meta = data_dir / 'meta.json'
    rows = sum(s['rows'] for s in json.loads(meta.read_text(encoding='utf-8'))['dates'].values()) if meta.exists() else 0
    codes = set()
    for p in data_dir.glob('*.json'):
        if DATE_FILE.match(p.name):
            for r in json.loads(p.read_text(encoding='utf-8')):
                codes.update((r['seatOriStaCode'], r['seatDstStaCode']))
    return rows, codes


def main():
    raw = (ROOT / '.cache/seat.json').read_bytes()
    try:
        source = json.loads(raw)
    except ValueError as e:
        sys.exit(f'source is not valid JSON: {e}')
    now = datetime.datetime.now(TAIPEI)
    data_dir = ROOT / 'data'
    published_rows, known_codes = published_state(data_dir)

    records, errors = validate(source, now.date().isoformat(), published_rows)
    if errors:
        sys.exit('refusing to publish:\n  ' + '\n  '.join(errors))

    warnings = drift(source, records, known_codes)
    (ROOT / '.cache/drift.txt').write_text(''.join(w + '\n' for w in warnings), encoding='utf-8')
    for w in warnings:
        print('WARNING', w)

    meta = build_meta(records, hashlib.sha256(raw).hexdigest(), now)
    changed = publish(data_dir, render(records), meta)
    print(f'{len(records)} records, {len(meta["dates"])} days, {"changed" if changed else "no change"}')


if __name__ == '__main__':
    main()
