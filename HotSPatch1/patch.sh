#!/bin/sh
# HotSPatch1 - Linux / macOS 启动脚本
# 用法: 把 boot.img 和本目录放在一起，然后执行  ./patch.sh
set -eu

cd "$(dirname "$0")"

PY=""
for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
        PY="$c"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "[-] 没有找到 python3。"
    echo "    Linux:  sudo apt install python3    (Debian/Ubuntu)"
    echo "            sudo pacman -S python       (Arch)"
    echo "    macOS:  brew install python3        或从 python.org 安装"
    exit 1
fi

exec "$PY" boot_patch.py "$@"
