#!/usr/bin/env bash
# 在部署主機上彙總網站的 access log。用法：tools/report.sh [天數，預設 7]
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
: "${DEPLOY_HOST:?在 .env 設定 DEPLOY_HOST（ssh 主機別名）}"
ssh "$DEPLOY_HOST" "python3 ${DEPLOY_DIR:-cgany-revival}/tools/access_report.py ${DEPLOY_DATA:-cgany-data}/logs ${1:-7}"
