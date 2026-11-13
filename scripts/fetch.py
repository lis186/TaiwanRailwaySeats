"""Download the TRA remaining-seats file to .cache/seat.json."""
import hashlib
import os
import sys
import time
import urllib.request

URL = 'https://ods.railway.gov.tw/tra-ods-web/ods/download/dataResource/5a2e672be26f4467a98f121d9ef43885'
OUT = '.cache/seat.json'


def download():
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.read()
        except Exception as e:
            err = e
            print(f'attempt {attempt + 1} failed: {e}', file=sys.stderr)
            time.sleep(10)
    raise err


body = download()
os.makedirs('.cache', exist_ok=True)
with open(OUT + '.tmp', 'wb') as f:
    f.write(body)
os.replace(OUT + '.tmp', OUT)
print(f'{len(body)} bytes, sha256 {hashlib.sha256(body).hexdigest()}')
