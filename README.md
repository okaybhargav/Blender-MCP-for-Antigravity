# Blender MCP Server

Local Model Context Protocol (MCP) server for Blender integration in Antigravity.

## Directory Overview

- `.venv/` - Dedicated Python virtual environment with `mcp-for-blender` v2.1.9 installed.
- `addon/` - Pre-packaged Blender add-on files (`addon.py`, `blender_mcp.py`).
- `run.bat` - Runs the Blender MCP server executable directly.
- `install_addon.bat` - Installs or updates the add-on into Blender's user addons folder.

## Integration in Antigravity (`mcp_config.json`)

The server is registered in `C:\Users\Okay Bhargav\.gemini\config\mcp_config.json`:

```json
{
  "mcpServers": {
    "blender": {
      "command": "C:\\MCP\\Blender MCP\\.venv\\Scripts\\mcp-for-blender.exe",
      "args": []
    }
  }
}
```

## How It Works

1. **Blender Addon**: An add-on runs inside Blender that starts a local socket server on `127.0.0.1:9876`.
2. **MCP Bridge Server**: The `mcp-for-blender.exe` process bridges Antigravity tool calls to the Blender socket server.
3. **Capabilities**:
   - `execute_blender_code`: Executes arbitrary Python code with the complete `bpy` API.
   - `get_scene_info`: Retrieves active objects, scene scale, camera settings, and materials.
   - `look`: Captures viewport screenshots or renders views.
   - `generate_3d`: AI 3D asset generation.
   - `search_assets` / `import_asset`: Free 3D models from Poly Haven, Sketchfab, and Poly Pizza.

## Installed Addon Location
- `C:\Users\Okay Bhargav\AppData\Roaming\Blender Foundation\Blender\5.2\scripts\addons\addon.py`
