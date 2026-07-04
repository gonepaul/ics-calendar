import json
import re
import html as html_lib
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from http.client import IncompleteRead

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'tdf2026_results.json'
STAGE_BASE = 'https://www.letour.fr/en/stage-{}'
RANKING_BASE = 'https://www.letour.fr/en/rankings/stage-{}'
UA = 'Mozilla/5.0 (compatible; gonepaul-ics-calendar/1.0)'


def load_results():
    if RESULTS.exists():
        return json.loads(RESULTS.read_text(encoding='utf-8'))
    return {'updated_at': None, 'stages': {}}


def save_results(data):
    RESULTS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def get(url):
    req = Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en,zh-CN;q=0.8'})
    with urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')


def strip_tags(s):
    s = re.sub(r'<script[\s\S]*?</script>', ' ', s, flags=re.I)
    s = re.sub(r'<style[\s\S]*?</style>', ' ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def html_unescape(s):
    return html_lib.unescape(s or '')


def parse_rankings_stage(stage, html):
    # Official rankings table rows contain rank, rider name, bib, team and time.
    # We locate the first rider-name link in the stage ranking table, then parse its row.
    name_pos = html.find('rankingTables__row__profile--name')
    if name_pos < 0:
        return None
    row_start = html.rfind('<tr', 0, name_pos)
    row_end = html.find('</tr>', name_pos)
    if row_start < 0 or row_end < 0:
        return None
    row = html[row_start:row_end + 5]
    cells = re.findall(r'<td[^>]*>([\s\S]*?)</td>', row, re.I)
    clean = [html_unescape(strip_tags(c)).strip() for c in cells]
    clean = [c for c in clean if c]
    name_match = re.search(r'class="rankingTables__row__profile--name"[^>]*>\s*([^<]+?)\s*</a>', row, re.I)
    if not name_match:
        return None
    winner = html_unescape(name_match.group(1)).strip()
    # Expected: ['1', 'J. VINGEGAARD', '11', 'TEAM VISMA | LEASE A BIKE', "00h 21' 47''", '-', '-', '-']
    if not clean or clean[0] != '1':
        return None
    team = clean[3] if len(clean) >= 4 else ''
    time_result = clean[4] if len(clean) >= 5 else ''
    if not winner or not time_result:
        return None
    return {
        'completed': True,
        'winner': winner,
        'time': time_result,
        'yellow_jersey': winner,
        'team': team,
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'sequence': 2,
        'source': RANKING_BASE.format(stage),
    }


def parse_stage_page(stage, html):
    text = strip_tags(html)
    patterns = [
        r'Stage\s+winner\s*[:\-]\s*([A-Z][A-Za-zÀ-ÖØ-öø-ÿ .\'\-]+)',
        r'Winner\s*[:\-]\s*([A-Z][A-Za-zÀ-ÖØ-öø-ÿ .\'\-]+)',
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            winner = m.group(1).strip(' .-')
            if 3 <= len(winner) <= 80:
                return {'completed': True, 'winner': winner, 'time': '', 'yellow_jersey': '', 'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), 'sequence': 2, 'source': STAGE_BASE.format(stage)}
    return None


def fetch_stage_result(stage):
    # Prefer official classification page; fallback to stage page.
    try:
        html = get(RANKING_BASE.format(stage))
        result = parse_rankings_stage(stage, html)
        if result:
            return result
    except (URLError, HTTPError, TimeoutError, IncompleteRead, OSError) as e:
        print(f'stage {stage}: rankings fetch failed: {e}')
    try:
        html = get(STAGE_BASE.format(stage))
        return parse_stage_page(stage, html)
    except (URLError, HTTPError, TimeoutError, IncompleteRead, OSError) as e:
        print(f'stage {stage}: stage fetch failed: {e}')
    return None


def main():
    data = load_results()
    stages = data.setdefault('stages', {})
    changed = False
    for stage in range(1, 22):
        key = str(stage)
        if stages.get(key, {}).get('completed'):
            continue
        result = fetch_stage_result(stage)
        if result:
            stages[key] = result
            changed = True
            data['updated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            save_results(data)
            print(f'stage {stage}: completed winner={result["winner"]} time={result.get("time", "")}')
        else:
            print(f'stage {stage}: no result')
    if changed:
        data['updated_at'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        save_results(data)
        print('updated results')
    else:
        print('no changes')

if __name__ == '__main__':
    main()
