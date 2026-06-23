#!/usr/bin/env bash
# 在 macOS 上打包 milodi 为独立可执行目录（无需目标机器安装 Python）。
#
# 要求：
#   - Python 3.10 或 3.11（与 pyproject.toml 一致）
#   - 在目标架构上构建（Apple Silicon 打 arm64，Intel Mac 打 x86_64）
#
# 用法：
#   ./scripts/build_macos.sh
#   ./scripts/build_macos.sh --onefile   # 单文件（启动慢，排错难，不推荐）
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

ONEFILE=""
if [[ "${1:-}" == "--onefile" ]]; then
  ONEFILE="--onefile"
  echo "警告: --onefile 模式体积大、冷启动慢，建议默认 onedir"
fi

"$PY" -m PyInstaller packaging/milodi.spec --noconfirm --clean $ONEFILE

OUT="$ROOT/dist/milodi/milodi"
if [[ -x "$OUT" ]]; then
  echo ""
  echo "构建完成: $OUT"
  echo "分发整个目录 dist/milodi/（或打成 .tar.gz）"
  echo "测试: $OUT --help"
else
  echo "未找到可执行文件，请检查 PyInstaller 输出" >&2
  exit 1
fi
