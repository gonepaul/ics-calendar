import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'tdf2026_results.json'
BASE = 'https://www.letour.fr/en/stage-{}'
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


def parse_stage_result(stage, html):
    text = strip_tags(html)
    patterns = [
        r'Stage\s+winner\s*[:\-]\s*([A-Z][A-Za-zÀ-ÖØ-öø-ÿ .\'\-]+)',
        r'Winner\s*[:\-]\s*([A-Z][A-Za-zÀ-ÖØ-öø-ÿ .\'\-]+)',
        r'won\s+stage\s+%d\s+[^.]*?\bby\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ .\'\-]+)' % stage,
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            winner = m.group(1).strip(' .-')
            if 3 <= len(winner) <= 80:
                return {'completed': True, 'winner': winner, 'time': '', 'yellow_jersey': '', 'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), 'sequence': 2, 'source': BASE.format(stage)}
    if re.search(r'(stage\s+classification|stage\s+ranking|stage\s+winner|results)', text, re.I):
        m = re.search(r'\b1\s+([A-Z][A-Za-zÀ-ÖØ-öø-ÿ .\'\-]{3,80})\s+(?:[A-Z]{2,3}|\d+h|\d+:\d+)', text)
        if m:
            winner = m.group(1).strip(' .-')
            return {'completed': True, 'winner': winner, 'time': '', 'yellow_jersey': '', 'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), 'sequence': 2, 'source': BASE.format(stage)}
    return None


def main():
    data = load_results()
    stages = data.setdefault('stages', {})
    changed = False
    for stage in range(1, 22):
        key = str(stage)
        if stages.get(key, {}).get('completed'):
            continue
        try:
            html = get(BASE.format(stage))
        except (URLError, HTTPError, TimeoutError) as e:
            print(f'stage {stage}: fetch failed: {e}')
            continue
        result = parse_stage_result(stage, html)
        if result:
            stages[key] = result
            changed = True
            print(f'stage {stage}: completed winner={result["winner"]}')
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
