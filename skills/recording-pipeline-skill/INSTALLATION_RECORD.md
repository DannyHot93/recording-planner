Installation & Automation Record

Date: 2026-03-08

Actions performed by assistant (자동화 설치):
- Added cleanup_old_parsed.py to scripts/ (moves parsed/media older than retention to backup_old_parsed/; --force to delete)
- Added GitHub Actions workflow .github/workflows/cleanup-parsed.yml to run cleanup daily at 03:00 KST
- Added process_inbound.py to scripts/ to OCR and create parsed entries from media/inbound, regenerate site, and commit & push
- Added launchd plist at launchd/com.recording-planner.process-inbound.plist to watch media/inbound and run process_inbound.py on changes
- Commit & pushed all changes to origin/main

Notes:
- OCR requires tesseract or pytesseract for best results. If not installed, process_inbound.py will still create parsed entries but raw_text may be empty.
- To publish to gh-pages, run: ./skills/recording-pipeline-skill/install.sh --force-ghpages (careful: force push).

Files added/modified:
- scripts/cleanup_old_parsed.py
- .github/workflows/cleanup-parsed.yml
- scripts/process_inbound.py
- launchd/com.recording-planner.process-inbound.plist
- backup_old_parsed/ (moved files during test run)

Keep this file with the skill so future installs/rollbacks remember what was configured.
