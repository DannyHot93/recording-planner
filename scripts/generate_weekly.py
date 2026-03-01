#!/usr/bin/env python3
import json,glob,os
from datetime import datetime
from dateutil import parser
from jinja2 import Environment, FileSystemLoader

PARSED_DIR = os.path.join('parsed')
OUT_DIR = os.path.join('web-output')
TEMPLATE_DIR = os.path.join('templates')

os.makedirs(OUT_DIR, exist_ok=True)

WEEKDAYS = ['월','화','수','목','금','토','일']

def weekday_key(date_str):
    try:
        dt = parser.isoparse(date_str)
    except Exception:
        return None
    # Python weekday(): Monday=0
    return dt.weekday()


def load_parsed():
    items = []
    for p in glob.glob(os.path.join(PARSED_DIR,'*.json')):
        try:
            with open(p,'r',encoding='utf-8') as f:
                j = json.load(f)
            fields = j.get('fields',{})
            start = fields.get('record_datetime_guess_start')
            end = fields.get('record_datetime_guess_end')
            if start:
                dt = parser.isoparse(start)
                date_iso = dt.date().isoformat()
                time = dt.time().strftime('%H:%M')
                if end:
                    t2 = parser.isoparse(end).time().strftime('%H:%M')
                    time = f"{time} - {t2}"
            else:
                date_iso = ''
                time = ''
            items.append({
                'date': date_iso,
                'time': time,
                'program': fields.get('program',''),
                'producer': fields.get('producer',''),
                'location': fields.get('location',''),
                'notes': fields.get('notes',''),
                'image': os.path.join('media', os.path.basename(j.get('source_file',''))),
                'weekday': weekday_key(fields.get('record_datetime_guess_start') or '')
            })
        except Exception as e:
            print('skip',p,e)
    # filter items with valid date and group by weekday
    buckets = {i: [] for i in range(7)}
    for it in items:
        if it.get('weekday') is not None:
            buckets[it['weekday']].append(it)
    # ensure order Mon..Sun
    ordered = []
    for i in range(7):
        # sort each day's items by date/time
        day_items = sorted(buckets[i], key=lambda x: x.get('date') or '')
        ordered.append((WEEKDAYS[i], day_items))
    return ordered

week = load_parsed()
# collect images
images = []
for day, items in week:
    for it in items:
        if it.get('image'):
            images.append(it['image'])

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
template = env.get_template('weekly_template.html.j2')
html = template.render(now=datetime.now().isoformat(), week=week, images=images)
with open(os.path.join(OUT_DIR,'index.html'),'w',encoding='utf-8') as f:
    f.write(html)
print('generated web-output/index.html')
