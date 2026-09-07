@echo off
cd /d %~dp0
where python >nul 2>nul
if %errorlevel%==0 (
  python start_showcase.py
) else (
  python3 start_showcase.py
)
pause
