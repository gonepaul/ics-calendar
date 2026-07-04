from datetime import datetime, timezone
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'tdf2026_beijing.ics'
RESULTS = ROOT / 'tdf2026_results.json'
now_dt = datetime.now(timezone.utc)
now = now_dt.strftime('%Y%m%dT%H%M%SZ')

events = [
(1,'20260704T230500','20260705T011600','Barcelone > Barcelone','19.6 km','Team Time-Trial','https://www.letour.fr/en/stage-1'),
(2,'20260705T194500','20260705T234600','Tarragone > Barcelone','168.5 km','Flat/Hilly','https://www.letour.fr/en/stage-2'),
(3,'20260706T181000','20260706T232300','Granollers > Les Angles','195.9 km','Mountain','https://www.letour.fr/en/stage-3'),
(4,'20260707T191000','20260707T234700','Carcassonne > Foix','181.9 km','Hilly','https://www.letour.fr/en/stage-4'),
(5,'20260708T200500','20260708T235600','Lannemezan > Pau','158.3 km','Flat','https://www.letour.fr/en/stage-5'),
(6,'20260709T182500','20260710T000500','Pau > Gavarnie-Gèdre','186.2 km','Mountain','https://www.letour.fr/en/stage-6'),
(7,'20260710T191500','20260710T233500','Hagetmau > Bordeaux','175.1 km','Flat','https://www.letour.fr/en/stage-7'),
(8,'20260711T191500','20260711T234300','Périgueux > Bergerac','180.4 km','Hilly','https://www.letour.fr/en/stage-8'),
(9,'20260712T193500','20260713T001000','Malemort > Ussel','185.5 km','Hilly','https://www.letour.fr/en/stage-9'),
(10,'20260714T191000','20260714T233600','Aurillac > Le Lioran','166.6 km','Mountain','https://www.letour.fr/en/stage-10'),
(11,'20260715T195000','20260715T235000','Vichy > Nevers','161.3 km','Flat','https://www.letour.fr/en/stage-11'),
(12,'20260716T193000','20260716T235000','Circuit Nevers Magny-Cours > Chalon-sur-Saône','179.1 km','Flat','https://www.letour.fr/en/stage-12'),
(13,'20260717T190000','20260718T001200','Dole > Belfort','205.8 km','Mountain','https://www.letour.fr/en/stage-13'),
(14,'20260718T191000','20260718T235200','Mulhouse > Le Markstein Fellering','155.3 km','Mountain','https://www.letour.fr/en/stage-14'),
(15,'20260719T191000','20260720T001100','Champagnole > Plateau de Solaison','183.9 km','Mountain','https://www.letour.fr/en/stage-15'),
(16,'20260721T190000','20260721T235000','Évian-les-Bains > Thonon-les-Bains','26.1 km','Individual time-trial','https://www.letour.fr/en/stage-16'),
(17,'20260722T192000','20260722T233900','Chambery > Voiron','174.7 km','Hilly','https://www.letour.fr/en/stage-17'),
(18,'20260723T183500','20260723T234000','Voiron > Orcières-Merlette','185.2 km','Mountain','https://www.letour.fr/en/stage-18'),
(19,'20260724T200000','20260724T234400',"Gap > Alpe d'Huez",'127.9 km','Mountain','https://www.letour.fr/en/stage-19'),
(20,'20260725T172000','20260725T225000',"Le Bourg d'Oisans > Alpe d'Huez",'170.9 km','Mountain','https://www.letour.fr/en/stage-20'),
(21,'20260726T221500','20260727T015000','Thoiry > Paris Champs-Élysées','133 km','Flat','https://www.letour.fr/en/stage-21'),
]

def esc(s):
    return str(s).replace('\\','\\\\').replace(';','\\;').replace(',','\\,').replace('\n','\\n')

def fold(line):
    out = []
    while len(line.encode('utf-8')) > 73:
        cut = 0
        size = 0
        for idx, ch in enumerate(line):
            b = len(ch.encode('utf-8'))
            if size + b > 73:
                break
            size += b
            cut = idx + 1
        out.append(line[:cut])
        line = ' ' + line[cut:]
    out.append(line)
    return '\r\n'.join(out)

def calendar_refresh_interval(now_dt, events, stage_results):
    """Return an RFC5545 duration tuned around expected stage finishes.

    Strategy:
    - Before race week: daily refresh.
    - On/near race days before finish: schedule next refresh close to expected finish.
    - From 30 min before expected finish until 3 h after finish, refresh every 5 min
      while the stage has no result yet.
    - After today's result is in, back off to 6 h until next stage day, otherwise daily.
    """
    from datetime import timedelta
    bj = timezone(timedelta(hours=8))
    now_bj = now_dt.astimezone(bj)
    pending_windows = []
    next_end = None
    for stage, start, end, *_ in events:
        completed = bool(stage_results.get(stage, {}).get('completed'))
        end_dt = datetime.strptime(end, '%Y%m%dT%H%M%S').replace(tzinfo=bj)
        if not completed:
            if end_dt >= now_bj:
                next_end = end_dt if next_end is None else min(next_end, end_dt)
            pending_windows.append((stage, end_dt))
    for stage, end_dt in pending_windows:
        if end_dt - timedelta(minutes=30) <= now_bj <= end_dt + timedelta(hours=3):
            return 'PT5M'
    if next_end is None:
        return 'P7D'
    delta = next_end - now_bj
    if delta <= timedelta(hours=6):
        return 'PT30M'
    if delta <= timedelta(days=1):
        return 'PT2H'
    if delta <= timedelta(days=3):
        return 'PT6H'
    return 'P1D'


if not RESULTS.exists():
    RESULTS.write_text(json.dumps({"updated_at": None, "stages": {}}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
results = json.loads(RESULTS.read_text(encoding='utf-8'))
stage_results = {int(k): v for k, v in results.get('stages', {}).items()}
refresh_interval = calendar_refresh_interval(now_dt, events, stage_results)

lines = [
'BEGIN:VCALENDAR',
'VERSION:2.0',
'PRODID:-//Tour de France 2026//Beijing Time Calendar//CN',
'CALSCALE:GREGORIAN',
'METHOD:PUBLISH',
'X-WR-CALNAME:2026环法自行车赛',
'X-WR-TIMEZONE:Asia/Shanghai',
'X-WR-CALDESC:2026 Tour de France schedule and results in Beijing Time - 21 stages',
f'REFRESH-INTERVAL;VALUE=DURATION:{refresh_interval}',
f'X-PUBLISHED-TTL:{refresh_interval}',
'BEGIN:VTIMEZONE',
'TZID:Asia/Shanghai',
'X-LIC-LOCATION:Asia/Shanghai',
'BEGIN:STANDARD',
'DTSTART:19700101T000000',
'TZOFFSETFROM:+0800',
'TZOFFSETTO:+0800',
'TZNAME:CST',
'END:STANDARD',
'END:VTIMEZONE',
]

for stage, start, end, route, dist, typ, url in events:
    r = stage_results.get(stage, {})
    completed = bool(r.get('completed'))
    sequence = int(r.get('sequence', 1))
    if completed:
        winner = r.get('winner', '赛段冠军待补')
        time_result = r.get('time', '')
        yellow = r.get('yellow_jersey', '')
        summary = f'✅ 环法2026 第{stage}赛段: {winner}'
        status = '已完赛'
    else:
        winner = ''
        time_result = ''
        yellow = ''
        summary = f'⏳ 环法2026 第{stage}赛段: {route}'
        status = '未开赛'
    desc_lines = [
        '2026 环法自行车赛',
        f'第 {stage} 赛段｜{route}',
        '',
        '【赛段信息】',
        f'类型：{typ}',
        f'距离：{dist}',
        f'北京时间：{start[9:11]}:{start[11:13]}',
        f'状态：{status}',
    ]
    if completed:
        desc_lines += [
            '',
            '【赛果】',
            f'赛段冠军：{winner}',
        ]
        if time_result:
            desc_lines += [f'冠军成绩：{time_result}']
        if yellow:
            desc_lines += [f'黄衫 / 总成绩领先：{yellow}']
        if r.get('updated_at'):
            desc_lines += [f'赛果更新时间：{r["updated_at"]}']
    desc_lines += [
        '',
        '【来源】',
        url,
    ]
    desc = '\n'.join(desc_lines)
    lines += [
        'BEGIN:VEVENT',
        f'UID:tdf2026-stage-{stage}@tourdefrance2026',
        f'DTSTAMP:{now}',
        f'CREATED:{now}',
        f'LAST-MODIFIED:{now}',
        f'SEQUENCE:{sequence}',
        f'DTSTART;TZID=Asia/Shanghai:{start}',
        f'DTEND;TZID=Asia/Shanghai:{end}',
        fold('SUMMARY:' + esc(summary)),
        fold('DESCRIPTION:' + esc(desc)),
        fold('LOCATION:' + esc(route)),
        'CLASS:PUBLIC',
        'CATEGORIES:环法自行车赛,Tour de France,2026,Cycling',
        'X-APPLE-TRAVEL-ADVISORY-BEHAVIOR:DISABLED',
        'STATUS:CONFIRMED',
        'TRANSP:OPAQUE',
        'BEGIN:VALARM',
        'TRIGGER:-PT30M',
        'ACTION:DISPLAY',
        fold('DESCRIPTION:' + esc(summary + ' 即将开始')),
        'END:VALARM',
        'END:VEVENT',
    ]
lines.append('END:VCALENDAR')
OUT.write_text('\r\n'.join(lines) + '\r\n', encoding='utf-8')
print(OUT)
