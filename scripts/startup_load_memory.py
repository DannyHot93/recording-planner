#!/usr/bin/env python3
"""
startup_load_memory.py

Load Recording Planner memory file into workspace-level MEMORY.md if missing/updated.
Intended to be run at session start.
"""
import os
from datetime import datetime

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MEM_FILE = os.path.join(BASE, 'memory', '2026-03-08-recording-planner.md')
WORK_MEM = os.path.join(BASE, 'MEMORY.md')

def load_text(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

if __name__ == '__main__':
    src = load_text(MEM_FILE)
    if not src:
        print('Source memory file not found:', MEM_FILE)
        raise SystemExit(1)
    summary = []
    summary.append('Recording Planner automation')
    summary.append('\n- Last updated: {}'.format(datetime.now().strftime('%Y-%m-%d')))
    summary.append('- Summary: Automated recording-planner pipeline installed. See memory/2026-03-08-recording-planner.md in workspace for details.')
    summary.append('- Details saved: origin repo clone path, scripts/process_inbound.py, scripts/cleanup_old_parsed.py, launchd plist, GitHub Actions workflow, backup behavior, and installation notes in memory/2026-03-08-recording-planner.md')
    summary.append('- Skill package: skills/recording-pipeline-skill')
    summary_text = '\n'.join(summary) + '\n\nSource: memory/2026-03-08-recording-planner.md#1\n'

    # Read existing MEMORY.md if present and compare
    existing = load_text(WORK_MEM) or ''
    if summary_text.strip() in existing:
        print('MEMORY.md already contains recording-planner summary. No change.')
        print('Done')
        raise SystemExit(0)

    # Write/replace top-level content
    with open(WORK_MEM, 'w', encoding='utf-8') as f:
        f.write(summary_text)
    print('Updated', WORK_MEM)
    print(summary_text)
    print('Done')
