#!/usr/bin/env python3
"""
Cleanup parsed entries and related media when their recording date is older than retention days.
Default behavior: move parsed JSON and referenced media to backup/old_parsed/YYYYMMDD/ (safe)
To permanently delete, pass --force
Usage: python3 scripts/cleanup_old_parsed.py [--days N] [--force]
"""
import json,glob,os,shutil,sys
from datetime import datetime,timedelta
from dateutil import parser
from zoneinfo import ZoneInfo

WORKDIR = os.path.dirname(os.path.dirname(__file__))
PARSED_DIR = os.path.join(WORKDIR, 'parsed')
MEDIA_DIR = os.path.join(WORKDIR, 'media')
BACKUP_DIR = os.path.join(WORKDIR, 'backup_old_parsed')

# defaults
RETENTION_DAYS = 7
FORCE = False

# simple arg parsing
args = sys.argv[1:]
if '--force' in args:
    FORCE = True
if '--days' in args:
    try:
        i = args.index('--days')
        RETENTION_DAYS = int(args[i+1])
    except Exception:
        print('Invalid --days usage; using default',RETENTION_DAYS)

now = datetime.now(ZoneInfo('Asia/Seoul'))
cutoff = now - timedelta(days=RETENTION_DAYS)

os.makedirs(BACKUP_DIR, exist_ok=True)

removed = []

for p in sorted(glob.glob(os.path.join(PARSED_DIR,'*.json'))):
    try:
        with open(p,'r',encoding='utf-8') as f:
            j = json.load(f)
    except Exception as e:
        print('skip unreadable',p,e)
        continue
    fields = j.get('fields',{}) if isinstance(j.get('fields'), dict) else j
    # prefer explicit record_datetime_guess_start; fall back to created_at
    date_str = fields.get('record_datetime_guess_start') or j.get('created_at') or fields.get('record_datetime_raw')
    if not date_str:
        # no date info: skip (do not delete)
        print('no date for',p,'-> skipping')
        continue
    try:
        dt = parser.isoparse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('Asia/Seoul'))
    except Exception:
        # if created_at present, try parse; else skip
        try:
            dt = parser.isoparse(j.get('created_at'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo('Asia/Seoul'))
        except Exception:
            print('cannot parse date for',p,'-> skipping')
            continue
    if dt < cutoff:
        # candidate for removal
        src_media = None
        source_file = j.get('source_file') or j.get('fields',{}).get('source_image_basename')
        if source_file:
            # normalize to media basename
            basename = os.path.basename(source_file)
            candidate = os.path.join(MEDIA_DIR, basename)
            if os.path.exists(candidate):
                src_media = candidate
        print('will remove:',p,'media:',src_media)
        if FORCE:
            # permanent delete
            try:
                os.remove(p)
                if src_media:
                    os.remove(src_media)
                removed.append((p,src_media))
            except Exception as e:
                print('error deleting',p,e)
        else:
            # move to backup dir with date-based subfolder
            sub = now.strftime('%Y%m%d_%H%M%S')
            dest_dir = os.path.join(BACKUP_DIR, sub)
            os.makedirs(dest_dir, exist_ok=True)
            try:
                shutil.move(p, dest_dir)
                if src_media:
                    shutil.move(src_media, dest_dir)
                removed.append((p,src_media, dest_dir))
            except Exception as e:
                print('error moving',p,e)

print('done. summary: removed count=', len(removed))
if not FORCE:
    print('Files were moved to',BACKUP_DIR,'. Use --force to permanently delete.')
else:
    print('Files permanently deleted (force).')
