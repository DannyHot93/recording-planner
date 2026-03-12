Recording Pipeline Skill

This skill packages the recording request pipeline used in the workspace. It contains generator scripts, cleanup, and helper commands to install and restore the site.

Included files:
- scripts/regenerate_show_all.py (generator to show ALL parsed events)
- scripts/cleanup_old_parsed.py (cleanup script: delete parsed files older than 7 days)
- install.sh (install script to copy files and optionally deploy to gh-pages with force)

Usage:
1. Run install.sh with optional argument `--force-ghpages` to force-push gh-pages.
   Example: ./install.sh --force-ghpages

Safety:
- The cleanup script performs permanent deletions (no backup). The install script will commit and may force-push gh-pages if requested.
