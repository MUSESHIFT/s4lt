"""Debug page for troubleshooting."""

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from s4lt.web.paths import get_templates_dir
from s4lt.config.settings import get_settings
from s4lt import __version__

router = APIRouter(prefix="/debug", tags=["debug"])
templates = Jinja2Templates(directory=get_templates_dir())
logger = logging.getLogger(__name__)


@router.get("", response_class=HTMLResponse)
async def debug_page(request: Request):
    """Show debug information for troubleshooting."""
    # Get system info
    try:
        from s4lt.logging import get_system_info, get_recent_logs, get_log_file
        system_info = get_system_info()
        recent_logs = get_recent_logs(50)
        log_file = get_log_file()
    except ImportError:
        system_info = {"error": "Logging module not available"}
        recent_logs = []
        log_file = None

    # Get settings
    try:
        settings = get_settings()
        settings_dict = {
            "mods_path": str(settings.mods_path) if settings.mods_path else None,
            "tray_path": str(settings.tray_path) if settings.tray_path else None,
            "deck_mode": settings.deck_mode,
        }
    except Exception as e:
        settings_dict = {"error": str(e)}

    # Get scan statistics
    scan_stats = {}
    try:
        if settings.mods_path and settings.mods_path.exists():
            package_count = len(list(settings.mods_path.rglob("*.package")))
            ts4script_count = len(list(settings.mods_path.rglob("*.ts4script")))
            disabled_count = len(list(settings.mods_path.rglob("*.disabled")))
            scan_stats = {
                "package_files": package_count,
                "ts4script_files": ts4script_count,
                "disabled_files": disabled_count,
                "mods_path_exists": True,
            }
        else:
            scan_stats = {"mods_path_exists": False}
    except Exception as e:
        scan_stats = {"error": str(e)}

    # Build HTML response
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug - S4LT</title>
        <style>
            body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            h1 {{ color: #4dabf7; }}
            h2 {{ color: #69db7c; margin-top: 24px; }}
            .section {{ background: #2d2d44; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #3d3d5c; }}
            th {{ color: #868e96; font-weight: normal; width: 200px; }}
            td {{ font-family: monospace; word-break: break-all; }}
            .logs {{ background: #1a1a2e; padding: 12px; border-radius: 4px; max-height: 400px; overflow-y: auto; font-family: monospace; font-size: 11px; white-space: pre-wrap; }}
            a {{ color: #4dabf7; }}
            .nav {{ margin-bottom: 20px; }}
            .error {{ color: #ff6b6b; }}
            .success {{ color: #69db7c; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="nav">
                <a href="/">← Back to Dashboard</a> | <a href="/settings">Settings</a>
            </div>

            <h1>S4LT Debug Information</h1>

            <h2>System Info</h2>
            <div class="section">
                <table>
                    <tr><th>S4LT Version</th><td>{system_info.get('s4lt_version', 'unknown')}</td></tr>
                    <tr><th>Python Version</th><td>{system_info.get('python_version', 'unknown')}</td></tr>
                    <tr><th>Platform</th><td>{system_info.get('platform', 'unknown')}</td></tr>
                    <tr><th>Qt Version</th><td>{system_info.get('qt_version', 'unknown')}</td></tr>
                    <tr><th>PyQt Version</th><td>{system_info.get('pyqt_version', 'unknown')}</td></tr>
                    <tr><th>Frozen (PyInstaller)</th><td>{system_info.get('frozen', False)}</td></tr>
                    <tr><th>MEIPASS</th><td>{system_info.get('meipass', 'N/A')}</td></tr>
                    <tr><th>Log File</th><td>{log_file or 'Not set'}</td></tr>
                </table>
            </div>

            <h2>Configuration</h2>
            <div class="section">
                <table>
                    <tr><th>Mods Path</th><td>{settings_dict.get('mods_path', 'Not set')}</td></tr>
                    <tr><th>Tray Path</th><td>{settings_dict.get('tray_path', 'Not set')}</td></tr>
                    <tr><th>Deck Mode</th><td>{settings_dict.get('deck_mode', 'Not set')}</td></tr>
                </table>
            </div>

            <h2>Scan Statistics</h2>
            <div class="section">
                <table>
                    <tr><th>Mods Path Exists</th><td class="{'success' if scan_stats.get('mods_path_exists') else 'error'}">{scan_stats.get('mods_path_exists', 'Unknown')}</td></tr>
                    <tr><th>.package Files</th><td>{scan_stats.get('package_files', 'N/A')}</td></tr>
                    <tr><th>.ts4script Files</th><td>{scan_stats.get('ts4script_files', 'N/A')}</td></tr>
                    <tr><th>.disabled Files</th><td>{scan_stats.get('disabled_files', 'N/A')}</td></tr>
                </table>
            </div>

            <h2>Recent Logs</h2>
            <div class="section">
                <button onclick="copyLogs()" style="background: #4dabf7; color: #000; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-bottom: 12px; font-size: 16px;">📋 Copy Logs to Clipboard</button>
                <span id="copyStatus" style="margin-left: 10px; color: #69db7c;"></span>
                <textarea id="logArea" readonly style="width: 100%; height: 400px; background: #1a1a2e; color: #eee; border: 1px solid #3d3d5c; border-radius: 4px; padding: 12px; font-family: monospace; font-size: 12px; resize: vertical;">{''.join(recent_logs) if recent_logs else 'No logs available'}</textarea>
            </div>
        </div>
        <script>
        function copyLogs() {{
            var textarea = document.getElementById('logArea');
            textarea.select();
            textarea.setSelectionRange(0, 99999);
            navigator.clipboard.writeText(textarea.value).then(function() {{
                document.getElementById('copyStatus').textContent = '✓ Copied!';
                setTimeout(function() {{ document.getElementById('copyStatus').textContent = ''; }}, 3000);
            }}).catch(function() {{
                document.execCommand('copy');
                document.getElementById('copyStatus').textContent = '✓ Copied!';
            }});
        }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
