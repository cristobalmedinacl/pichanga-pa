@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py server.py
  goto :eof
)
where python >nul 2>nul
if %errorlevel%==0 (
  python server.py
  goto :eof
)
echo No se encontro Python.
echo Instala Python desde https://www.python.org/downloads/
echo En el instalador marca "Add python.exe to PATH".
pause
