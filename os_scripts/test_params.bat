@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === без параметров ===
python emulator.py
echo === только VFS ===
python emulator.py --vfs vfs\sample.json
echo === только скрипт ===
python emulator.py --script scripts\startup.txt
echo === VFS и скрипт ===
python emulator.py --vfs vfs\sample.json --script scripts\startup.txt
