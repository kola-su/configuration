@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === без параметров ===
python src\emulator.py
echo === битый JSON ===
python src\emulator.py --vfs vfs\broken.json
echo === только скрипт ===
python src\emulator.py --script scripts\startup_errors.txt
echo === отсутствующий файл и скрипт ===
python src\emulator.py --vfs vfs\missing.json --script scripts\startup_errors.txt
