@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
echo Installing Blender MCP Addon into user addons folder...
"%SCRIPT_DIR%.venv\Scripts\mcp-for-blender.exe" install-addon
echo.
echo Addon installed! If Blender is currently running:
echo 1. Open Edit -^> Preferences -^> Add-ons
echo 2. Search for "Interface: Blender MCP"
echo 3. Disable and re-enable it, or restart Blender.
echo 4. Click "Start MCP Server" in the Blender 3D View sidebar.
pause
endlocal
