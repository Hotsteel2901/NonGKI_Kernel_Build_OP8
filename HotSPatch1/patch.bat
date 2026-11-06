@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [-] 没有找到 Python。
    echo     请到 https://www.python.org/downloads/ 安装 Python 3，
    echo     安装时勾选 "Add Python to PATH"，然后重新运行本脚本。
    pause
    exit /b 1
)

%PY% boot_patch.py %*
echo.
pause
