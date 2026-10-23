#!/usr/bin/env bash
# 把 override／vBulletin 資料同步到部署主機，並在那裡更新程式、重啟。用法：tools/deploy.sh [--data]
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
: "${DEPLOY_HOST:?在 .env 設定 DEPLOY_HOST（ssh 主機別名）}"
DEPLOY_DIR="${DEPLOY_DIR:-cgany-revival}"
DEPLOY_DATA="${DEPLOY_DATA:-cgany-data}"

if [ -n "$(git status --porcelain -- revive compose.yaml)" ]; then
  echo "revive/ 或 compose.yaml 有還沒 commit 的改動，先 commit 並 push" >&2; exit 1
fi
git fetch -q
if [ "$(git rev-parse HEAD)" != "$(git rev-parse '@{u}')" ]; then
  echo "本機跟 origin 不同步，先 push 或 pull" >&2; exit 1
fi

rsync -a --delete --chmod=D755,F644 "$CGANY_DATA/cgany_build/" "$DEPLOY_HOST:$DEPLOY_DATA/cgany_build/"
if [ "${1:-}" = "--data" ]; then
  rsync -a --chmod=D755,F644 "$CGANY_DATA/cgany_archive" "$CGANY_DATA/cgany_com_archive" "$DEPLOY_HOST:$DEPLOY_DATA/"
fi
ssh "$DEPLOY_HOST" "cd $DEPLOY_DIR && git pull -q --ff-only && docker compose --profile tunnel up -d --build && docker compose restart revive"
echo "deployed $(git rev-parse --short HEAD) to $DEPLOY_HOST"
