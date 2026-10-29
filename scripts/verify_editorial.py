#!/usr/bin/env python3
"""Check rendered home against published source tables, without browser JS."""
import html
import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
site = Path(sys.argv[1])
home = (site / 'index.html').read_text()

for category, slug, selector, name_col in [('boxoffice', 'daily-boxoffice', 'movie', 2), ('drama-ratings', 'weekly-drama-ratings', 'drama', 3)]:
    latest = sorted((root / '_posts').glob(f'*{slug}*.md'))[-1]
    text = latest.read_text()
    rows = [line.split('|') for line in text.splitlines() if re.match(r'^\|\s*\d+\s*\|', line)][:5]
    assert len(rows) == 5, latest
    blocks = re.findall(rf'<a class="{selector}" .*?</a>', home, re.S)
    assert len(blocks) == 5, (category, len(blocks))
    for row, block in zip(rows, blocks):
        name = html.unescape(re.sub(r'<[^>]+>', '', row[name_col])).strip()
        assert html.escape(name) in block or name in html.unescape(block), name
        if category == 'boxoffice':
            assert f'data-daily="{row[4].strip()}"' in block
            assert f'data-total="{row[5].strip()}"' in block
        else:
            assert f'>{round(float(row[4]), 1)}<small>%' in block, block
    print(f'{category}: latest source {latest.name}, TOP 5 values match')

for href in set(re.findall(r'href="(/[^"?#]*)', home)):
    target = site / href.lstrip('/')
    if href.endswith('/'):
        target /= 'index.html'
    assert target.exists(), href
assert 'rel="canonical" href="https://screen-score.sooyadev.com/"' in home
assert '<meta name="robots" content="noindex' not in home
assert not (site / 'scripts/verify_editorial.py').exists()
print('Home local links, canonical, indexability, tooling exclusion: OK')
