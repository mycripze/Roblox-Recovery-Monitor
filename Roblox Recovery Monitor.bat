@echo off
cd /d "%~dp0"
python "%~dp0roblox_recovery.py"
if errorlevel 1 pause
