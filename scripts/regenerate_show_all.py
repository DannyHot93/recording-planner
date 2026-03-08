#!/usr/bin/env python3
# Regenerate site to show ALL parsed events (past and future), grouped by weekday
import json,glob,os
from datetime import datetime,timedelta
from dateutil import parser
from zoneinfo import ZoneInfo

WEEKDAYS = ['월','화','수','목','금','토','일']
now = datetime.now(ZoneInfo('Asia/Seoul'))

parsed = []
for p in sorted(glob.glob('parsed/*.json')):
    try:
        j = json.load(open(p,encoding='utf-8'))
    except Exception:
        continue
    fields = j.get('fields') if isinstance(j.get('fields'), dict) else j
    start = fields.get('record_datetime_guess_start')
    if not start:
        # include items without start but mark date empty
        _id = (fields.get('program','') + '_unknown_' + os.path.basename(p)).replace(' ','_')
        parsed.append({'id':_id,'weekday':'','date':'','time':'','program':fields.get('program',''),'producer':fields.get('producer',''),'location':fields.get('location',''),'notes':fields.get('notes',''),'dt_iso':'9999-12-31T23:59:59+09:00'})
        continue
    try:
        dt = parser.isoparse(start)
    except Exception:
        continue
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo('Asia/Seoul'))
    dt_local = dt.astimezone(ZoneInfo('Asia/Seoul'))
    wd = WEEKDAYS[dt_local.weekday()]
    _id = (fields.get('program','') + '_' + dt_local.date().isoformat() + '_' + dt_local.time().strftime('%H:%M')).replace(' ','_')
    parsed.append({'id':_id,'weekday':wd,'date':dt_local.date().isoformat(),'time':dt_local.time().strftime('%H:%M'),'program':fields.get('program',''),'producer':fields.get('producer',''),'location':fields.get('location',''),'notes':fields.get('notes',''),'dt_iso':dt_local.isoformat()})

# sort by datetime (placing unknowns at end)
parsed.sort(key=lambda x: x.get('dt_iso','9999-12-31T23:59:59+09:00'))

# compute this_week for styling
monday = now
while monday.weekday() != 0:
    monday -= timedelta(days=1)
week_start = monday.replace(hour=0,minute=0,second=0,microsecond=0)
week_end = week_start + timedelta(days=7)
this_week = [it for it in parsed if it.get('dt_iso')!='9999-12-31T23:59:59+09:00' and week_start <= parser.isoparse(it['dt_iso']) < week_end]
this_week_ids = set([it['id'] for it in this_week])

out = {'generated_at': now.isoformat(), 'items': parsed, 'this_week': this_week}

os.makedirs('web-output', exist_ok=True)
open('web-output/data.json','w',encoding='utf-8').write(json.dumps(out,ensure_ascii=False,indent=2))
open('data.json','w',encoding='utf-8').write(json.dumps(out,ensure_ascii=False,indent=2))

# build html similar to previous styled template
html = []
html.append('<!doctype html>')
html.append('<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>주간계획표</title>')
html.append('<style>')
html.append('body{font-family:Arial,sans-serif;padding:18px;font-size:22px;line-height:1.35}')
html.append('.two-column{display:flex;gap:24px;align-items:flex-start;flex-wrap:wrap}')
html.append('.left-col{flex:0 0 40%;min-width:260px}')
html.append('.right-col{flex:1 1 58%;min-width:360px}')
html.append('.week-summary{background:#fff8e1;padding:18px;border-radius:10px;margin-bottom:18px}')
html.append('.week-day{background:transparent;border:none;padding:6px;margin-bottom:6px}')
html.append('.day-title-small{font-weight:900;display:inline-block;margin-bottom:6px;font-size:1.1rem;color:#222}')
html.append('.day-title{font-weight:800;font-size:2.0rem;margin-bottom:10px;display:flex;align-items:center;gap:12px}')
html.append('.day-badge{display:inline-block;width:44px;height:44px;border-radius:8px;background:#ffd54f;color:#111;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:1.2rem}')
html.append('.day-title-text{font-size:1.4rem;font-weight:800}')
html.append('table{border-collapse:collapse;width:100%;font-size:1.08rem}')
html.append('th,td{border:1px solid #333;padding:10px;word-break:break-word;white-space:normal}')
html.append('th{background:#eee;font-weight:800;font-size:1.1rem}')
html.append('.this-week-row{background:#e8f6ff}')
html.append('.other-week-row{background:transparent;color:#444}')
html.append('@media(max-width:800px){ .left-col{flex-basis:100%} .right-col{flex-basis:100%} body{font-size:18px} }')
html.append('</style>')
html.append('</head><body>')
html.append('<!-- build: '+now.isoformat()+' -->')
html.append('<div id="main">')
html.append('<h1>주간계획표</h1>')
html.append('<p id="generated">생성일: '+now.isoformat()+'</p>')
html.append('<div class="two-column">')
html.append('<div class="left-col">')
html.append('<div class="week-summary"><h2 class="day-title">이번 주 일정 요약</h2>')
for d in WEEKDAYS:
    items = [it for it in this_week if it['weekday']==d]
    html.append('<div class="week-day"><div class="day-title-small">'+d+'</div>')
    if not items:
        html.append('<div>해당 요일에 예정된 녹화가 없습니다.</div>')
    else:
        html.append('<ul>')
        for it in items:
            html.append('<li>'+it['date']+' '+it['time']+' — '+it['program']+' ('+it.get('producer','')+')'+'</li>')
        html.append('</ul>')
    html.append('</div>')
html.append('</div></div>')
html.append('<div class="right-col">')
for d in WEEKDAYS:
    items = [it for it in parsed if it['weekday']==d]
    html.append('<div class="day-section" id="day-'+d+'">')
    html.append('<div class="day-title"><span class="day-badge">'+d+'</span><span class="day-title-text">'+d+'</span></div>')
    if not items:
        html.append('<div class="list">해당 요일에 예정된 녹화가 없습니다.</div>')
    else:
        html.append('<div class="list">')
        html.append('<table><tr><th>날짜</th><th>시간</th><th>프로그램</th><th>PD</th><th>장소</th><th>메모</th></tr>')
        import html as _html
        for it in items:
            cls = 'this-week-row' if it['id'] in this_week_ids else 'other-week-row'
            notes = _html.escape(it.get('notes','') or '')
            notes = notes.replace('\n','<br>')
            program = _html.escape(it.get('program','') or '')
            producer = _html.escape(it.get('producer','') or '')
            location = _html.escape(it.get('location','') or '')
            html.append('<tr class="'+cls+'" data-id="'+it['id']+'"><td>'+_html.escape(it.get('date',''))+'</td><td>'+_html.escape(it.get('time',''))+'</td><td>'+program+'</td><td>'+producer+'</td><td>'+location+'</td><td>'+notes+'</td></tr>')
        html.append('</table>')
        html.append('</div>')
    html.append('</div>')
html.append('</div>')
html.append('</div>')
html.append('</div>')
html.append('</body></html>')
open('web-output/index.html','w',encoding='utf-8').write('\n'.join(html))
open('index.html','w',encoding='utf-8').write('\n'.join(html))
print('wrote web-output/index.html and data.json and repo-root index.html (showing ALL parsed)')