#!/usr/bin/env bash
# 构建 macOS 桌面应用 Milodi.app：双击后台启动 Web 服务并打开浏览器。
#
# 用法：
#   ./scripts/build_macos_app.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "此脚本仅适用于 macOS" >&2
  exit 1
fi

PY="${PYTHON:-python3.11}"
if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PY="$ROOT/.venv/bin/python"
fi

echo "使用 Python: $($PY --version) ($($PY -c 'import platform; print(platform.machine())'))"

"$PY" -m pip install ".[web]" pyinstaller -q

if [[ ! -f "$ROOT/packaging/icon/Milodi.icns" ]]; then
  echo "未找到图标，正在生成 Milodi.icns …"
  "$ROOT/scripts/build_icon.sh" "$ROOT/packaging/icon/milodi-1024.png"
fi

"$PY" -m PyInstaller packaging/milodi_app.spec --noconfirm --clean

OUT="$ROOT/dist/Milodi.app"
if [[ -d "$OUT" ]]; then
  echo ""
  echo "构建完成: $OUT"
  echo "双击 Milodi.app 即可使用；也可执行: open dist/Milodi.app"
  echo "分发建议: cd dist && zip -r Milodi-macos-arm64.zip Milodi.app"
else
  echo "未找到 Milodi.app，请检查 PyInstaller 输出" >&2
  exit 1
fi
