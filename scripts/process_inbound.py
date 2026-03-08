#!/usr/bin/env python3
"""
Process inbound media images: move to media/, run OCR (tesseract or pytesseract), extract dates and basic fields,
create parsed/*.json entries (one per detected date), regenerate site, and commit & push.

Usage: python3 scripts/process_inbound.py [--move-only]
"""
import os,sys,glob,shutil,subprocess,json,re
from datetime import datetime
from dateutil import parser
from zoneinfo import ZoneInfo

BASE = os.path.dirname(os.path.dirname(__file__))
INBOUND = os.path.join(BASE, '..', 'media', 'inbound')
INBOUND = os.path.normpath(os.path.join(BASE, 'media', '..', 'media', '..', 'media', 'inbound'))
# fallback if above odd path
if not os.path.exists(INBOUND):
    INBOUND = os.path.join(BASE, 'media', 'inbound')
MEDIA_DIR = os.path.join(BASE, 'media')
PARSED_DIR = os.path.join(BASE, 'parsed')

os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(PARSED_DIR, exist_ok=True)

# helpers
DATE_RE = re.compile(r'(20\d{2}|\d{2})[.\-/년\s]*(0?[1-9]|1[0-2])[.\-/월\s]*(0?[1-9]|[12][0-9]|3[01])')
FULL_DATE_RE = re.compile(r'(20\d{2})[.\-/년\s]*(0?[1-9]|1[0-2])[.\-/월\s]*(0?[1-9]|[12][0-9]|3[01])')


def run_tesseract(path):
    # try tesseract CLI
    try:
        out = subprocess.check_output(['tesseract', path, 'stdout'], stderr=subprocess.DEVNULL, timeout=20)
        return out.decode('utf-8')
    except Exception:
        return None


def try_pytesseract(path):
    try:
        from PIL import Image
        import pytesseract
        txt = pytesseract.image_to_string(Image.open(path), lang='kor+eng')
        return txt
    except Exception:
        return None


def extract_dates(txt):
    dates = []
    for m in FULL_DATE_RE.finditer(txt):
        y,mn,d = m.groups()
        try:
            dt = datetime(int(y), int(mn), int(d), tzinfo=ZoneInfo('Asia/Seoul'))
            dates.append(dt)
        except Exception:
            continue
    # fallback: two-digit year -> assume 20xx
    if not dates:
        for m in DATE_RE.finditer(txt):
            y,mn,d = m.groups()
            y = y if len(y)==4 else ('20'+y)
            try:
                dt = datetime(int(y), int(mn), int(d), tzinfo=ZoneInfo('Asia/Seoul'))
                dates.append(dt)
            except Exception:
                continue
    return dates


def make_parsed_entry(basename, raw_text, dates):
    # if no dates, create single ambiguous entry with created_at
    entries = []
    if not dates:
        created = datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
        j = {
            'id': basename,
            'source_file': os.path.join('web-output','media',basename),
            'raw_text': raw_text,
            'fields': {
                'program': '',
                'producer': '',
                'record_datetime_raw': '',
                'record_datetime_guess_start': '',
                'record_datetime_guess_end': '',
                'location': '',
                'notes': ''
            },
            'created_at': created
        }
        entries.append(j)
        return entries
    for dt in dates:
        # default time: 00:00
        start_iso = dt.isoformat()
        j = {
            'id': f"{os.path.splitext(basename)[0]}_{dt.date().isoformat()}",
            'source_file': os.path.join('web-output','media',basename),
            'raw_text': raw_text,
            'fields': {
                'program': '',
                'producer': '',
                'record_datetime_raw': dt.date().isoformat(),
                'record_datetime_guess_start': start_iso,
                'record_datetime_guess_end': start_iso,
                'location': '',
                'notes': ''
            },
            'created_at': datetime.now(ZoneInfo('Asia/Seoul')).isoformat()
        }
        entries.append(j)
    return entries


def main():
    inbound_glob = os.path.join(BASE, 'media', 'inbound', '*')
    files = glob.glob(inbound_glob)
    if not files:
        print('no inbound files')
        return
    any_created = False
    for f in files:
        try:
            basename = os.path.basename(f)
            dest = os.path.join(MEDIA_DIR, basename)
            shutil.move(f, dest)
            print('moved',basename,'to media/')
            # OCR
            txt = run_tesseract(dest)
            if not txt:
                txt = try_pytesseract(dest)
            if not txt:
                txt = ''
            dates = extract_dates(txt)
            entries = make_parsed_entry(basename, txt, dates)
            for e in entries:
                pid = e['id']
                path = os.path.join(PARSED_DIR, pid + '.json')
                with open(path,'w',encoding='utf-8') as wf:
                    json.dump(e, wf, ensure_ascii=False, indent=2)
                print('wrote parsed',path)
                any_created = True
        except Exception as ex:
            print('error processing',f,ex)
    if any_created:
        # regenerate site
        try:
            subprocess.check_call(['python3','scripts/regenerate_all_future.py'])
        except Exception:
            try:
                subprocess.check_call(['python3','scripts/generate_weekly.py'])
            except Exception:
                print('failed to regenerate site')
        # commit & push
        try:
            subprocess.check_call(['git','add','media','parsed','web-output','data.json','index.html'])
            subprocess.check_call(['git','commit','-m','ci: process inbound media and regenerate site'])
            subprocess.check_call(['git','push','origin','main'])
        except Exception as e:
            print('git commit/push failed',e)

if __name__=='__main__':
    main()
