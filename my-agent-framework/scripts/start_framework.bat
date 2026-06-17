@echo off
REM start_framework.bat — Windows version
echo ========================================
echo   Agent Framework - Starting Server
echo ========================================

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

if exist config\.env (
    for /f "tokens=1,2 delims==" %%a in (config\.env) do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" set "%%a=%%b"
    )
    echo [OK] Loaded config\.env
)

echo [OK] Starting API server...
python -m uvicorn framework.api.server:app --host 0.0.0.0 --port 8000 --reload
pause
