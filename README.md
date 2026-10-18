# Blender MCP for Antigravity

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Blender Version](https://img.shields.io/badge/Blender-3.6%20%7C%204.x%20%7C%205.x-orange.svg)](https://www.blender.org/)
[![Model Context Protocol](https://img.shields.io/badge/Protocol-MCP-blue.svg)](https://modelcontextprotocol.io/)

A production-ready **Model Context Protocol (MCP)** server and addon integration that connects **Google Antigravity** (and other MCP clients such as Claude Desktop and Cursor) directly to **Blender 3D**.

It allows AI assistants to understand your Blender 3D scene, generate and run `bpy` Python automation code, create complex 3D objects, capture viewport renders, and search and import 3D assets using natural language.

---

## 📖 Table of Contents
- [What is it & Why Use It?](#-what-is-it--why-use-it)
- [How It Works (Architecture)](#-how-it-works-architecture)
- [Key Features & Tools](#-key-features--tools)
- [Prerequisites](#-prerequisites)
- [Step-by-Step Setup Guide](#-step-by-step-setup-guide)
  - [Step 1: Clone the Repository](#step-1-clone-the-repository)
  - [Step 2: Environment Setup](#step-2-environment-setup)
  - [Step 3: Install the Blender Add-on](#step-3-install-the-blender-add-on)
  - [Step 4: Enable & Start Addon in Blender](#step-4-enable--start-addon-in-blender)
  - [Step 5: Configure Google Antigravity](#step-5-configure-google-antigravity)
- [Prompt Examples for Antigravity](#-prompt-examples-for-antigravity)
- [Project Structure](#-project-structure)
- [Troubleshooting & FAQ](#-troubleshooting--faq)
- [License](#-license)

---

## 💡 What is it & Why Use It?

Blender is an incredibly capable 3D creation suite, but scripting and scene setup often require writing repetitive `bpy` scripts or clicking through deeply nested menus. 

**Blender MCP for Antigravity** bridges that gap:
- You chat in natural language with Antigravity ("*Create a neon cyberpunk street lamp with emission materials and a camera pointed at it*").
- Antigravity queries the active scene layout, writes and executes the appropriate Blender Python (`bpy`) commands, inspects the result via viewport screenshots, and iterates until the scene is complete.
- It turns Blender into an AI-augmented 3D studio.

---

## 🏗️ How It Works (Architecture)

```text
┌───────────────────────────────────────┐
│     Google Antigravity / MCP Client   │
└───────────────────┬───────────────────┘
                    │  (stdio JSON-RPC protocol)
                    ▼
┌───────────────────────────────────────┐
│      Blender MCP Server Process       │
│    (run.bat / mcp-for-blender.exe)    │
└───────────────────┬───────────────────┘
                    │  (Local TCP Socket: 127.0.0.1:9876)
                    ▼
┌───────────────────────────────────────┐
│      Blender Addon (addon.py)         │
│   Running inside Blender 3D process   │
└───────────────────┬───────────────────┘
                    │  (Direct bpy API calls)
                    ▼
┌───────────────────────────────────────┐
│     Blender 3D Viewport & Scene       │
└───────────────────────────────────────┘
```

1. **Blender Addon (`addon/addon.py`)**: Runs directly inside Blender and starts a background TCP socket listener on `127.0.0.1:9876`.
2. **MCP Bridge Server (`mcp-for-blender`)**: A lightweight Python service started by Antigravity via standard input/output (`stdio`).
3. **Execution Loop**: When Antigravity invokes an MCP tool, the bridge forwards the command to the Blender socket. The addon executes the Python snippet using Blender's internal Python interpreter (`bpy`), formats the result or screenshot, and responds back to Antigravity.

---

## ⚡ Key Features & Tools

| Tool Name | Description |
|---|---|
| `execute_blender_code` | Executes arbitrary Python code with the complete `bpy` API (mesh creation, materials, modifiers, animation keyframes, cameras, lighting). |
| `get_scene_info` | Retrieves active scene hierarchy, selected objects, dimensions, materials, camera transforms, and world settings. |
| `look` | Captures a viewport screenshot or camera view render and returns it to Antigravity to visually inspect results. |
| `search_assets` | Searches free 3D models from Poly Haven, Sketchfab, and Poly Pizza. |
| `import_asset` | Downloads and imports the chosen 3D model directly into the active scene. |
| `generate_3d` | Integrates with AI 3D generation pipelines (such as Hunyuan3D / Tripo3D). |

---

## 📋 Prerequisites

- **Operating System**: Windows 10 or 11 (64-bit)
- **Blender**: Blender 3.6 LTS, 4.x, or 5.x installed
- **Python**: Python 3.10+ installed and added to your system `PATH`
- **MCP Client**: Google Antigravity, Claude Desktop, or Cursor

---

## 🚀 Step-by-Step Setup Guide

### Step 1: Clone the Repository
Open PowerShell or Command Prompt:
```cmd
git clone https://github.com/okaybhargav/Blender-MCP-for-Antigravity.git "C:\MCP\Blender MCP"
cd "C:\MCP\Blender MCP"
```

### Step 2: Environment Setup
We provide an automated setup script that creates the virtual environment and installs all dependencies:
```cmd
setup.bat
```

*(Manual alternative)*:
```cmd
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Install the Blender Add-on
Double-click or run:
```cmd
install_addon.bat
```
This automatically copies `addon/addon.py` into your Blender User Addons folder (`%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\`).

### Step 4: Enable & Start Addon in Blender
1. Launch **Blender**.
2. Open **Edit** > **Preferences** > **Add-ons**.
3. In the search bar, type `Blender MCP` (or `Interface: Blender MCP`).
4. **Check the box** to enable the addon.
5. In the 3D Viewport, press **`N`** on your keyboard to reveal the right sidebar tabs.
6. Click on the **Blender MCP** tab.
7. Click the **"Start MCP Server"** button.
   - The indicator will turn **Green** and display: `Status: Listening on port 9876`.

> [!TIP]
> Keep Blender open while using Antigravity so the socket server remains active.

### Step 5: Configure Google Antigravity
Open your Antigravity configuration file:
- File path: `C:\Users\<YourUsername>\.gemini\config\mcp_config.json`

Add the `blender` server definition under `mcpServers`:

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
*(If your repository is located in a different path, replace `C:\\MCP\\Blender MCP` with your actual cloned path).*

Restart Antigravity or reload MCP tools. You should now see the `blender` tools registered and ready!

---

## 💬 Prompt Examples for Antigravity

Once connected, you can ask Antigravity to do things like:

- *"Inspect my active Blender scene and tell me what objects and lights are currently present."*
- *"Create a procedural low-poly island with water, sand, rocks, and a palm tree."*
- *"Add a three-point lighting setup (Key, Fill, and Rim lights) pointing at the selected mesh."*
- *"Search Poly Haven for a wooden table asset and import it into the scene at coordinates (0, 0, 0)."*
- *"Take a viewport screenshot using the look tool to verify the materials."*

---

## 📁 Project Structure

```text
Blender-MCP-for-Antigravity/
├── addon/
│   ├── addon.py                  # Blender UI panel & socket server listener
│   └── blender_mcp.py            # Core bpy socket dispatcher
├── references/                   # Reference character sheets and turnaround visuals
├── build_clean_kid.py            # Procedural character builder script
├── build_master_character.py     # Advanced character modeling & rigging script
├── install_addon.bat             # One-click installer for Blender user addons folder
├── run.bat                       # CLI execution launcher
├── setup.bat                     # Automated venv creation & dependency installer
├── requirements.txt              # Python package dependencies (mcp-for-blender)
├── .gitignore                    # Excludes virtual environments and temporary files
├── LICENSE                       # MIT Open-Source License
└── README.md                     # Documentation
```

---

## ❓ Troubleshooting & FAQ

### 1. `Connection refused (127.0.0.1:9876)`
- **Reason**: The Blender add-on is either not installed or the socket server has not been started.
- **Fix**: Open Blender, press `N` in the 3D Viewport, click the `Blender MCP` tab, and click **"Start MCP Server"**. Verify that the status turns green.

### 2. Add-on doesn't show up in Blender Preferences
- **Reason**: The addon file was placed in an incorrect folder version.
- **Fix**: Check `C:\Users\<Username>\AppData\Roaming\Blender Foundation\Blender\<version>\scripts\addons\`. Ensure `addon.py` is inside that directory and restart Blender.

### 3. Antigravity says `mcp-for-blender.exe not found`
- **Reason**: Virtual environment was not built or the path in `mcp_config.json` is incorrect.
- **Fix**: Run `setup.bat` inside the project folder, and confirm that `C:\MCP\Blender MCP\.venv\Scripts\mcp-for-blender.exe` exists.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - free for personal and commercial open-source use.
