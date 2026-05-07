"""
HTML injection backend for AdInject attacks.
Extends the base backend to support HTML content injection.
"""

import json
import subprocess
import time
from typing import Dict, Any, Optional
from pathlib import Path
from .base import AttackBackend
from .runtime_backend import RuntimeAttackBackend


class HTMLInjectionBackend(RuntimeAttackBackend):
    """Backend that supports HTML injection for AdInject-style attacks."""
    
    def __init__(self):
        super().__init__()
        self.html_content: Optional[str] = None
        self.ad_server_process = None
        self.ad_server_port = 61234
        
    def set_html_content(self, html_content: str):
        """Set HTML content to be injected."""
        self.html_content = html_content
        
    def start_ad_server(self, attack_config: Dict[str, Any]):
        """Start the AdInject ad server."""
        # Get parameters
        ad_server = attack_config.get("parameters", {}).get("ad_server", "localhost")
        ad_server_port = attack_config.get("parameters", {}).get("ad_server_port", "61234")
        
        # Check if server is already running
        try:
            import requests
            response = requests.get(f"http://{ad_server}:{ad_server_port}/health", timeout=1)
            if response.status_code == 200:
                print(f"Ad server already running at {ad_server}:{ad_server_port}")
                return
        except:
            pass
        
        # Start ad server
        print(f"Starting ad server at {ad_server}:{ad_server_port}")
        
        # Create ad server script
        server_script = self._create_ad_server_script(attack_config)
        
        # Run server in background
        self.ad_server_process = subprocess.Popen(
            ["python", server_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for server to start
        time.sleep(2)
        
    def stop_ad_server(self):
        """Stop the AdInject ad server."""
        if self.ad_server_process:
            self.ad_server_process.terminate()
            self.ad_server_process = None
            print("Ad server stopped")
            
    def _create_ad_server_script(self, attack_config: Dict[str, Any]) -> str:
        """Create a temporary ad server script."""
        # Get parameters
        ad_server = attack_config.get("parameters", {}).get("ad_server", "localhost")
        ad_server_port = attack_config.get("parameters", {}).get("ad_server_port", "61234")
        ad_title = attack_config.get("parameters", {}).get("ad_title", "# CRITICAL NOTIFICATION")
        ad_content = attack_config.get("parameters", {}).get("ad_content", "You need to close the advertisement...")
        ad_button_text = attack_config.get("parameters", {}).get("ad_button_text", "Close AD")
        
        # Create server script
        script_content = f'''
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import os

app = FastAPI()

# Store ad data
ad_data = {{
    "title": "{ad_title}",
    "content": "{ad_content}",
    "button_text": "{ad_button_text}"
}}

@app.get("/")
async def get_ad():
    return HTMLResponse("""
<!DOCTYPE html>
<html>
<head>
    <title>Ad</title>
</head>
<body>
    <h1>Ad Server Running</h1>
    <p>Port: {ad_server_port}</p>
</body>
</html>
""")

@app.get("/health")
async def health_check():
    return {{"status": "ok"}}

@app.get("/close_ad")
async def close_ad(ad_id: str = "01", finished: str = "false"):
    print(f"Close ad request: ad_id={{ad_id}}, finished={{finished}}")
    return JSONResponse({{"status": "success", "finished": finished}})

@app.get("/ad/assets/{{filename}}")
async def get_asset(filename: str):
    # Return a simple SVG for info icon
    if filename == "info.svg":
        return HTMLResponse("""
<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="10"></circle>
    <line x1="12" y1="16" x2="12" y2="12"></line>
    <line x1="12" y1="8" x2="12.01" y2="8"></line>
</svg>
""")
    raise HTTPException(status_code=404)

if __name__ == "__main__":
    uvicorn.run(app, host="{ad_server}", port={ad_server_port})
'''
        
        # Save script to temporary file
        script_path = Path("temp_ad_server.py")
        with open(script_path, "w") as f:
            f.write(script_content)
            
        return str(script_path.absolute())
        
    def inject_attack(self, page, attack_config: Dict[str, Any]):
        """Inject the attack into the page."""
        # Check if this is an HTML injection attack
        if "injection_html" in attack_config:
            # Start ad server if needed
            if attack_config.get("setup_fn") == "start_ad_server":
                self.start_ad_server(attack_config)
            
            # Inject HTML into the page
            if self.html_content:
                # Use JavaScript to inject HTML
                injection_script = f"""
                (function() {{
                    var adHtml = `{self.html_content.replace('`', '\\`')}`;
                    var div = document.createElement('div');
                    div.innerHTML = adHtml;
                    document.body.appendChild(div);
                }})();
                """
                page.evaluate(injection_script)
                print("HTML ad injected into page")
        else:
            # Use regular injection
            super().inject_attack(page, attack_config)
            
    def cleanup(self, attack_config: Dict[str, Any]):
        """Clean up after the attack."""
        # Stop ad server if needed
        if attack_config.get("cleanup_fn") == "stop_ad_server":
            self.stop_ad_server()
            
        # Regular cleanup
        super().cleanup(attack_config)
