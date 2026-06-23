#!/usr/bin/env bash
# 从 1024px 源图生成 macOS Milodi.icns
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ICON_DIR="$ROOT/packaging/icon"
SRC="${1:-$ICON_DIR/milodi-1024.png}"
ICONSET="$ICON_DIR/icon.iconset"
OUT="$ICON_DIR/Milodi.icns"

if [[ ! -f "$SRC" ]]; then
  echo "源图不存在: $SRC" >&2
  echo "用法: $0 [path/to/source.png]" >&2
  exit 1
fi

rm -rf "$ICONSET"
mkdir -p "$ICONSET"

WORK="$ICON_DIR/.build-square.png"
W=$(sips -g pixelWidth "$SRC" | awk '/pixelWidth/ {print $2}')
H=$(sips -g pixelHeight "$SRC" | awk '/pixelHeight/ {print $2}')
MIN=$(( W < H ? W : H ))
sips -c "$MIN" "$MIN" "$SRC" --out "$WORK" >/dev/null
sips -z 1024 1024 "$WORK" --out "$ICON_DIR/milodi-1024.png" >/dev/null
BASE="$ICON_DIR/milodi-1024.png"

sips -z 16 16 "$BASE" --out "$ICONSET/icon_16x16.png" >/dev/null
sips -z 32 32 "$BASE" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
sips -z 32 32 "$BASE" --out "$ICONSET/icon_32x32.png" >/dev/null
sips -z 64 64 "$BASE" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
sips -z 128 128 "$BASE" --out "$ICONSET/icon_128x128.png" >/dev/null
sips -z 256 256 "$BASE" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
sips -z 256 256 "$BASE" --out "$ICONSET/icon_256x256.png" >/dev/null
sips -z 512 512 "$BASE" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
sips -z 512 512 "$BASE" --out "$ICONSET/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$BASE" --out "$ICONSET/icon_512x512@2x.png" >/dev/null

iconutil -c icns "$ICONSET" -o "$OUT"
rm -f "$WORK"
echo "已生成 $OUT"
