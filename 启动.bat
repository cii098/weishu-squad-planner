@echo off
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe" "%~dp0app.py"
) else (
    start "" pythonw "%~dp0app.py"
)
