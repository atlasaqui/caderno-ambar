@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
echo Abra http://127.0.0.1:8093/acompanhamento.html
.venv\Scripts\python.exe backend\aplicacao.py
pause
