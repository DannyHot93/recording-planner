#!/usr/bin/env bash
set -e
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="$(cd "${SKILL_DIR}/../.." && pwd)"
echo "Installing Recording Pipeline skill from ${SKILL_DIR} to workspace ${WORKDIR}"
# copy scripts
mkdir -p "${WORKDIR}/scripts"
cp -v "${SKILL_DIR}/../.."/scripts/*.py "${WORKDIR}/scripts/" || true
# copy cleanup script if missing
cp -v "${SKILL_DIR}/../.."/scripts/cleanup_old_parsed.py "${WORKDIR}/scripts/" || true
# ensure scripts executable
chmod +x "${WORKDIR}/scripts"/*.py || true
# regenerate site
cd "${WORKDIR}"
python3 scripts/regenerate_show_all.py || python3 scripts/regenerate_all_future.py || true
# commit changes
git add web-output/index.html web-output/data.json data.json index.html || true
git commit -m "install: recording-pipeline-skill - regenerate outputs" || true
# push main
git push origin main || true
# publish to gh-pages
if [ "$1" == "--force-ghpages" ]; then
  git checkout gh-pages || true
  cp -v index.html data.json web-output/data.json . || true
  git add index.html data.json web-output.data.json || true
  git commit -m "publish: install recording pipeline skill (force)" || true
  git push origin gh-pages --force || true
  git checkout main || true
  echo "Published to gh-pages (force)"
else
  echo "Skipping gh-pages force publish. Run with --force-ghpages to publish."
fi
