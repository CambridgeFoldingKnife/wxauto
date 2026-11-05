#!/usr/bin/env bash
# 健衡图片卡片渲染器：HTML -> 1086x1448 PNG（无头 Chrome）
# 用法:
#   bash render.sh              # 渲染本目录下所有 *.html
#   bash render.sh 01-cover.html
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$DIR/out"
mkdir -p "$OUT"

CHROME=""
for c in \
  "/c/Program Files/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe" \
  "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  "/c/Program Files/Microsoft/Edge/Application/msedge.exe" ; do
  [ -f "$c" ] && CHROME="$c" && break
done
if [ -z "$CHROME" ]; then echo "找不到 Chrome/Edge，无法渲染" >&2; exit 1; fi

render_one() {
  local file="$1"
  local base; base="$(basename "$file" .html)"
  local outpath="$OUT/$base.png"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=1 --window-size=1086,1448 \
    --default-background-color=FFFFFFFF \
    --screenshot="$outpath" "file://$(cygpath -m "$file" 2>/dev/null || echo "$file")" >/dev/null 2>&1
  echo "✓ out/$base.png"
}

if [ $# -gt 0 ]; then
  for f in "$@"; do render_one "$DIR/$f"; done
else
  shopt -s nullglob
  for f in "$DIR"/*.html; do
    case "$(basename "$f")" in _*) continue;; esac
    render_one "$f"
  done
fi
