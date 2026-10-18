@echo off
setlocal
echo ========================================================
echo Setting up Python virtual environment for Blender MCP...
echo ========================================================
python -m venv .venv
if errorlevel 1 (
    echo Error creating virtual environment. Please ensure Python 3.10+ is installed and on your PATH.
    pause
    exit /b 1
)
call .venv\Scripts\activate
pip install -r requirements.txt
if errorlevel 1 (
    echo Error installing dependencies.
    pause
    exit /b 1
)
echo.
echo ========================================================
echo Setup completed successfully!
echo You can now run run.bat or install_addon.bat
echo ========================================================
pause
endlocal
