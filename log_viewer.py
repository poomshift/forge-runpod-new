from flask import Flask, render_template_string, make_response, jsonify, send_file, request
import os
import threading
import time
import subprocess
import sys
import platform
import zipfile
import io
import urllib.parse
from flask_socketio import SocketIO, emit
from datetime import datetime

# Initialize Flask and SocketIO with CORS
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables to store logs
log_buffer = []
log_lock = threading.Lock()

# Add HTML_TEMPLATE before the routes
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ComfyUI Log Viewer</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #2563eb;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-color: #1e293b;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
            --progress-bg: #e2e8f0;
            --scrollbar-track: #f1f1f1;
            --scrollbar-thumb: #c1c1c1;
            --scrollbar-thumb-hover: #a8a8a8;
        }

        [data-theme="dark"] {
            --primary-color: #3b82f6;
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #e2e8f0;
            --text-secondary: #94a3b8;
            --border-color: #334155;
            --progress-bg: #334155;
            --scrollbar-track: #1e293b;
            --scrollbar-thumb: #475569;
            --scrollbar-thumb-hover: #64748b;
        }
        
        body { 
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 20px;
            background: var(--bg-color);
            color: var(--text-color);
            height: 100vh;
            box-sizing: border-box;
            transition: background-color 0.3s, color 0.3s;
        }
        
        .container {
            max-width: 100%;
            height: calc(100vh - 40px);
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .header {
            padding: 16px;
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        .header h1 {
            margin: 0;
            font-size: 24px;
            color: var(--text-color);
        }
        
        .main-content {
            display: flex;
            gap: 20px;
            flex: 1;
            min-height: 0;
        }
        
        .sidebar {
            width: 300px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            overflow-y: auto;
        }
        
        .logs-section {
            flex: 2;
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        
        .downloader-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 20px;
            overflow-y: auto;
        }
        
        .card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: background-color 0.3s;
            position: relative;
        }
        
        .card h2 {
            margin: 0 0 16px 0;
            font-size: 18px;
            color: var(--text-color);
        }
        
        .controls {
            margin: 16px 0;
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .divider {
            width: 1px;
            height: 24px;
            background: var(--border-color);
            margin: 0 4px;
        }
        
        #log-container {
            flex: 1;
            padding: 20px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 14px;
            line-height: 1.5;
            white-space: pre-wrap;
            overflow-y: auto;
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            color: var(--text-color);
            transition: background-color 0.3s, color 0.3s;
            min-height: 600px;
        }
        
        /* Scrollbar styling */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--scrollbar-track);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--scrollbar-thumb);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--scrollbar-thumb-hover);
        }

        /* Theme switch styles */
        .theme-switch {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .theme-switch .icon {
            font-size: 16px;
            line-height: 1;
            user-select: none;
        }

        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }

        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: var(--progress-bg);
            transition: .4s;
            border-radius: 24px;
        }

        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: var(--card-bg);
            transition: .4s;
            border-radius: 50%;
        }

        input:checked + .toggle-slider {
            background-color: var(--primary-color);
        }

        input:checked + .toggle-slider:before {
            transform: translateX(20px);
        }

        .auto-scroll-control {
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 1000;
            background: var(--card-bg);
            padding: 8px 16px;
            border-radius: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            color: var(--text-color);
            transition: background-color 0.3s, color 0.3s;
        }

        .download-button {
            display: inline-flex;
            align-items: center;
            padding: 8px 16px;
            background: var(--primary-color);
            color: white;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: background-color 0.3s;
        }
        
        .download-button:hover {
            background-color: #1d4ed8;
        }
        
        .comfyui-button {
            background-color: #10b981;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .comfyui-button:hover {
            background-color: #059669;
        }
        
        .comfyui-button.disabled {
            opacity: 0.6;
            cursor: not-allowed;
            pointer-events: none;
        }
        
        .arrow {
            font-size: 18px;
        }

        .download-form {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            margin-top: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .form-group {
            margin-bottom: 16px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: var(--text-color);
            font-weight: 500;
        }

        .form-group input[type="text"],
        .form-group input[type="url"],
        .form-group select {
            width: calc(100% - 24px);
            max-width: 400px;
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 14px;
        }

        .form-group .example-text {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        .form-group select {
            cursor: pointer;
        }

        #downloadStatus {
            margin-top: 12px;
            padding: 12px;
            border-radius: 6px;
            display: none;
        }

        .status-success {
            background: #dcfce7;
            color: #166534;
        }

        .status-error {
            background: #fee2e2;
            color: #991b1b;
        }
        
        /* Styles for installed nodes and models */
        .accordion-section {
            margin-bottom: 10px;
        }
        
        .accordion-header {
            background: var(--card-bg);
            padding: 10px 15px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-weight: 500;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            user-select: none;
        }
        
        .accordion-header:hover {
            background: var(--bg-color);
        }
        
        .accordion-content {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
        }
        
        .accordion-content.active {
            max-height: 500px;
            overflow-y: auto;
        }
        
        .model-item {
            margin: 10px 0 0 10px;
            padding: 8px 12px;
            background: var(--bg-color);
            border-radius: 4px;
            font-size: 13px;
        }
        
        .model-name {
            font-weight: 500;
            word-break: break-all;
        }
        
        .model-size {
            color: var(--text-secondary);
            font-size: 12px;
            margin-top: 4px;
        }
        
        .model-count-badge {
            background: var(--primary-color);
            color: white;
            border-radius: 12px;
            padding: 2px 8px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .refresh-button {
            position: absolute;
            top: 18px;
            right: 20px;
            background: transparent;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 12px;
            cursor: pointer;
            color: var(--text-secondary);
        }
        
        .refresh-button:hover {
            background: var(--bg-color);
            color: var(--text-color);
        }
        
        .notification {
            margin-top: 10px;
            padding: 12px;
            border-radius: 6px;
            background: #f0f9ff;
            color: #0369a1;
            display: none;
        }
        
        {% if is_runpod %}
        /* Additional RunPod-specific styles */
        .runpod-badge {
            display: inline-flex;
            align-items: center;
            background: rgba(0, 0, 0, 0.1);
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 12px;
            margin-left: 10px;
        }
        {% endif %}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        let socket;
        let autoScroll = true;
        let userScrolled = false;

        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            const themeToggle = document.getElementById('theme-toggle');
            
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            document.getElementById('theme-icon').textContent = 
                newTheme === 'dark' ? '🌙' : '☀️';
            
            themeToggle.checked = newTheme === 'dark';
        }

        function initializeTheme() {
            const savedTheme = localStorage.getItem('theme') || 'light';
            const themeToggle = document.getElementById('theme-toggle');
            
            document.documentElement.setAttribute('data-theme', savedTheme);
            document.getElementById('theme-icon').textContent = 
                savedTheme === 'dark' ? '🌙' : '☀️';
            themeToggle.checked = savedTheme === 'dark';
        }

        function initializeWebSocket() {
            socket = io();
            
            socket.on('new_log_line', function(data) {
                appendLogLine(data.line);
            });
            
            socket.on('logs', function(data) {
                document.getElementById('log-container').innerHTML = data.logs;
                if (autoScroll) {
                    scrollToBottom(document.getElementById('log-container'));
                }
            });
        }
        
        function appendLogLine(line) {
            const logContainer = document.getElementById('log-container');
            logContainer.innerHTML += line + '\\n';
            
            if (autoScroll && !userScrolled) {
                scrollToBottom(logContainer);
            }
        }
        
        function scrollToBottom(element) {
            element.scrollTop = element.scrollHeight;
        }
        
        function toggleAutoScroll() {
            autoScroll = !autoScroll;
            userScrolled = false;
            if (autoScroll) {
                const logContainer = document.getElementById('log-container');
                scrollToBottom(logContainer);
            }
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            initializeTheme();
            initializeWebSocket();
            initializeAccordions();
            
            const logContainer = document.getElementById('log-container');
            
            logContainer.addEventListener('scroll', function() {
                if (!isScrolledToBottom(logContainer)) {
                    userScrolled = true;
                } else {
                    userScrolled = false;
                }
            });
            
            scrollToBottom(logContainer);
            
            // Check if ComfyUI is running
            checkComfyUIStatus();
        });

        function isScrolledToBottom(element) {
            return Math.abs(element.scrollHeight - element.scrollTop - element.clientHeight) < 1;
        }
        
        function checkComfyUIStatus() {
            const comfyUrl = '{{ proxy_url }}';
            const statusElement = document.getElementById('comfyui-status');
            
            fetch(comfyUrl, { method: 'HEAD', mode: 'no-cors' })
                .then(() => {
                    // If we get here, the request didn't throw an error
                    statusElement.style.display = 'none';
                    document.getElementById('comfyui-button').classList.remove('disabled');
                })
                .catch(() => {
                    // Show notification that ComfyUI might not be ready
                    statusElement.style.display = 'block';
                    statusElement.textContent = 'ComfyUI may still be starting. Check logs for progress.';
                    // Check again in 10 seconds
                    setTimeout(checkComfyUIStatus, 10000);
                });
        }
        
        function toggleAccordion(element) {
            const content = element.nextElementSibling;
            content.classList.toggle('active');
            
            // Save state to localStorage
            const id = element.getAttribute('data-section');
            const isOpen = content.classList.contains('active');
            localStorage.setItem(`accordion_${id}`, isOpen ? 'open' : 'closed');
        }
        
        function initializeAccordions() {
            const headers = document.querySelectorAll('.accordion-header');
            headers.forEach(header => {
                const id = header.getAttribute('data-section');
                const content = header.nextElementSibling;
                
                // Restore state from localStorage
                const savedState = localStorage.getItem(`accordion_${id}`);
                if (savedState === 'open') {
                    content.classList.add('active');
                }
                
                header.addEventListener('click', () => {
                    toggleAccordion(header);
                });
            });
        }

        function refreshLogs() {
            fetch('/refresh_logs')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Logs refreshed successfully');
                    } else {
                        console.error('Error refreshing logs:', data.message);
                    }
                })
                .catch(error => {
                    console.error('Failed to refresh logs:', error);
                });
        }

        function downloadFromCivitai() {
            const url = document.getElementById('modelUrl').value;
            const apiKey = document.getElementById('apiKey').value;
            const modelType = document.getElementById('modelType').value;
            const statusDiv = document.getElementById('downloadStatus');
            
            statusDiv.className = '';
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Downloading...';
            
            fetch('/download/civitai', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    api_key: apiKey,
                    model_type: modelType
                })
            })
            .then(response => response.json())
            .then(data => {
                statusDiv.textContent = data.message;
                statusDiv.className = data.success ? 'status-success' : 'status-error';
            })
            .catch(error => {
                statusDiv.textContent = 'Error: ' + error.message;
                statusDiv.className = 'status-error';
                });
        }

        function downloadFromHuggingFace() {
            const url = document.getElementById('hfUrl').value;
            const modelType = document.getElementById('hfModelType').value;
            const statusDiv = document.getElementById('hfDownloadStatus');
            
            statusDiv.className = '';
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Downloading...';
            
            fetch('/download/huggingface', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: url,
                    model_type: modelType
                })
            })
            .then(response => response.json())
            .then(data => {
                statusDiv.textContent = data.message;
                statusDiv.className = data.success ? 'status-success' : 'status-error';
            })
            .catch(error => {
                statusDiv.textContent = 'Error: ' + error.message;
                statusDiv.className = 'status-error';
                });
        }
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="title-section">
                <h1>ComfyUI Log Viewer</h1>
            </div>
            <div class="controls">
                <div class="control-group">
                    <a href="/download/outputs" class="download-button">Download Outputs</a>
                    <a href="{{ proxy_url }}" target="_blank" id="comfyui-button" class="download-button comfyui-button">Open ComfyUI <span class="arrow">→</span></a>
                    <button onclick="refreshLogs()" class="download-button">Refresh Logs</button>
                    <div class="divider"></div>
                    <div class="theme-switch">
                        <span id="theme-icon" class="icon">☀️</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="theme-toggle" onchange="toggleTheme()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
                <div id="comfyui-status" class="notification">Checking ComfyUI status...</div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="sidebar">
                <!-- Custom Nodes Section -->
                <div class="card">
                    <h2>Installed Custom Nodes</h2>
                    <button onclick="window.location.reload()" class="refresh-button">Refresh</button>
                    <div class="accordion-section">
                        <div class="accordion-header" data-section="custom_nodes">
                            <span>Custom Nodes</span>
                            <span class="model-count-badge">{{ custom_nodes|length }}</span>
                        </div>
                        <div class="accordion-content">
                            {% if custom_nodes %}
                                {% for node in custom_nodes %}
                                    <div class="model-item">
                                        <div class="model-name">{{ node.name }}</div>
                                        <div class="model-size">{{ node.version }}</div>
                                    </div>
                                {% endfor %}
                            {% else %}
                                <div class="model-item">No custom nodes installed</div>
                            {% endif %}
                        </div>
                    </div>
                </div>
                
                <!-- Models Section -->
                <div class="card">
                    <h2>Installed Models <span class="model-count-badge">{{ total_models }}</span></h2>
                    <button onclick="window.location.reload()" class="refresh-button">Refresh</button>
                    {% if models %}
                        {% for category, items in models.items() %}
                            <div class="accordion-section">
                                <div class="accordion-header" data-section="{{ category }}">
                                    <span>{{ category }}</span>
                                    <span class="model-count-badge">{{ items|length }}</span>
                                </div>
                                <div class="accordion-content">
                                    {% for model in items %}
                                        <div class="model-item">
                                            <div class="model-name">{{ model.name }}</div>
                                            <div class="model-size">{{ model.size }}</div>
                                        </div>
                                    {% endfor %}
                                </div>
                            </div>
                        {% endfor %}
                    {% else %}
                        <div class="model-item">No models found</div>
                    {% endif %}
                </div>
            </div>
            
            <div class="logs-section">
                <div id="log-container">{{ logs }}</div>
            </div>

            <div class="downloader-section">
                <div class="card">
                    <h2>Civitai Model Downloader</h2>
                    <div class="form-group">
                        <label for="modelUrl">Model URL</label>
                        <input type="url" id="modelUrl" placeholder="Enter model URL" required>
                        <div class="example-text">Example: https://civitai.com/api/download/models/1399707</div>
                    </div>
                    <div class="form-group">
                        <label for="apiKey">API Key (Optional)</label>
                        <input type="text" id="apiKey" placeholder="Your Civitai API key">
                    </div>
                    <div class="form-group">
                        <label for="modelType">Model Type</label>
                        <select id="modelType">
                            <option value="diffusion_models">Diffusion Model</option>
                            <option value="loras">LORA</option>
                            <option value="checkpoints">Checkpoint</option>
                            <option value="vae">VAE</option>
                            <option value="unet">UNet</option>
                            <option value="text_encoders">Text Encoder</option>
                        </select>
                    </div>
                    <button onclick="downloadFromCivitai()" class="download-button">Download Model</button>
                    <div id="downloadStatus"></div>
                </div>

                <div class="card">
                    <h2>Hugging Face Downloader</h2>
                    <div class="form-group">
                        <label for="hfUrl">Model URL</label>
                        <input type="url" id="hfUrl" placeholder="Enter Hugging Face file URL" required>
                        <div class="example-text">Example: https://huggingface.co/[user]/[repo]/resolve/main/model.safetensors</div>
                    </div>
                    <div class="form-group">
                        <label for="hfModelType">Model Type</label>
                        <select id="hfModelType">
                            <option value="diffusion_models">Diffusion Model</option>
                            <option value="loras">LORA</option>
                            <option value="checkpoints">Checkpoint</option>
                            <option value="vae">VAE</option>
                            <option value="unet">UNet</option>
                            <option value="text_encoders">Text Encoder</option>
                        </select>
                    </div>
                    <button onclick="downloadFromHuggingFace()" class="download-button">Download Model</button>
                    <div id="hfDownloadStatus"></div>
                </div>
            </div>
        </div>
    </div>

    <div class="auto-scroll-control">
        <span>Auto-scroll</span>
        <label class="toggle-switch">
            <input type="checkbox" checked onchange="toggleAutoScroll()">
            <span class="toggle-slider"></span>
        </label>
    </div>
</body>
</html>
'''

def get_installed_custom_nodes():
    """Get a list of installed custom nodes"""
    custom_nodes_dir = os.path.join('/workspace', 'ComfyUI', 'custom_nodes')
    if not os.path.exists(custom_nodes_dir):
        return []
    
    nodes = []
    for item in os.listdir(custom_nodes_dir):
        item_path = os.path.join(custom_nodes_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            # Try to get version info from git if available
            version = "Installed"
            git_dir = os.path.join(item_path, '.git')
            if os.path.exists(git_dir):
                try:
                    result = subprocess.run(
                        ['git', 'describe', '--tags', '--always'],
                        cwd=item_path,
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        version = result.stdout.strip()
                except Exception:
                    pass
            
            nodes.append({
                'name': item,
                'path': item_path,
                'version': version
            })
    
    # Sort alphabetically
    return sorted(nodes, key=lambda x: x['name'].lower())

def get_installed_models():
    """Get a list of installed models by category"""
    models_dir = os.path.join('/workspace', 'ComfyUI', 'models')
    if not os.path.exists(models_dir):
        return {}
    
    result = {}
    for category in os.listdir(models_dir):
        category_path = os.path.join(models_dir, category)
        if os.path.isdir(category_path):
            model_files = []
            for file in os.listdir(category_path):
                file_path = os.path.join(category_path, file)
                if os.path.isfile(file_path) and not file.startswith('.'):
                    # Get file size in MB
                    file_size = os.path.getsize(file_path) / (1024 * 1024)
                    model_files.append({
                        'name': file,
                        'path': file_path,
                        'size': f"{file_size:.1f} MB"
                    })
            
            if model_files:
                # Sort by name
                model_files.sort(key=lambda x: x['name'].lower())
                result[category] = model_files
    
    # Sort categories alphabetically
    return dict(sorted(result.items()))
    log_file = os.path.join('logs', 'comfyui.log')
    
    if not os.path.exists(log_file):
        os.makedirs('logs', exist_ok=True)
        open(log_file, 'a').close()
    
    def follow(file_path):
        """Generator function that yields new lines in a file with proper handling of file rotation/truncation"""
        current_position = 0
        while True:
            try:
                # Re-open the file on each iteration to detect file truncation or rotation
                with open(file_path, 'r') as file:
                    # Check if file has been truncated
                    file_size = os.path.getsize(file_path)
                    if file_size < current_position:
                        current_position = 0  # File was truncated, start from beginning
                    
                    # Seek to last position
                    file.seek(current_position)
                    
                    # Read new lines
                    new_lines = file.readlines()
                    if new_lines:
                        current_position = file.tell()
                        for line in new_lines:
                            yield line
                    else:
                        # No new lines, sleep before checking again
                        time.sleep(0.1)
            except Exception as e:
                print(f"Error following log file: {e}")
                time.sleep(1)  # Wait a bit longer on error

    try:
        # Load initial content
        with open(log_file, 'r') as file:
            content = file.readlines()
            processed_content = []
            
            # Keep only the last 500 lines and filter duplicates
            content = content[-500:] if len(content) > 500 else content
            prev_line = None
            for line in content:
                stripped_line = line.strip()
                if stripped_line and stripped_line != prev_line:
                    processed_content.append(stripped_line)
                prev_line = stripped_line
            
            with log_lock:
                log_buffer.clear()
                log_buffer.extend(processed_content)
            
            # Emit initial logs
            socketio.emit('logs', {'logs': get_current_logs()})
        
        # Start the continuous tail
        prev_line = None
        for line in follow(log_file):
            stripped_line = line.strip()
            if stripped_line and stripped_line != prev_line:  # Only process non-empty lines and not duplicates
                with log_lock:
                    log_buffer.append(stripped_line)
                    if len(log_buffer) > 500:
                        log_buffer.pop(0)
                # Emit new log line via WebSocket
                socketio.emit('new_log_line', {'line': stripped_line})
            prev_line = stripped_line
    except Exception as e:
        print(f"Error tailing log file: {e}")
        time.sleep(5)

def tail_log_file():
    """Continuously tail the log file and update the buffer"""
    with log_lock:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"Log Viewer - Last {len(log_buffer)} lines (as of {timestamp})\n"
        header += "=" * 80 + "\n\n"
        
        # Return log buffer with duplicate consecutive lines removed
        if log_buffer:
            filtered_logs = []
            prev_line = None
            for line in log_buffer:
                if line != prev_line:
                    filtered_logs.append(line)
                prev_line = line
            return header + '\n'.join(filtered_logs)
        else:
            return header + "No logs yet."

def create_output_zip():
    """Create a zip file of the ComfyUI output directory"""
    output_dir = os.path.join('/workspace', 'ComfyUI', 'output')
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, output_dir)
                zf.write(file_path, arcname)
    
    memory_file.seek(0)
    return memory_file

def download_from_civitai(url, api_key=None, model_type="loras"):
    """Download a model from Civitai using aria2c"""
    model_dir = os.path.join('/workspace', 'ComfyUI', 'models', model_type)
    os.makedirs(model_dir, exist_ok=True)
    
    download_url = url
    if api_key:
        download_url = f"{url}?token={api_key}"
    
    cmd = [
        'aria2c',
        '--console-log-level=error',
        '-c',
        '-x', '16',
        '-s', '16',
        '-k', '1M',
        '--file-allocation=none',
        '--optimize-concurrent-downloads=true',
        '--max-connection-per-server=16',
        '--min-split-size=1M',
        '--max-tries=5',
        '--retry-wait=10',
        '--connect-timeout=30',
        '--timeout=600',
        download_url,
        '-d', model_dir
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "message": "Download completed successfully"}
        else:
            return {"success": False, "message": f"Download failed: {result.stderr}"}
    except Exception as e:
        return {"success": False, "message": f"Error during download: {str(e)}"}

def download_from_huggingface(url, model_type="loras"):
    """Download a model from Hugging Face using aria2c"""
    model_dir = os.path.join('/workspace', 'ComfyUI', 'models', model_type)
    os.makedirs(model_dir, exist_ok=True)
    
    try:
        filename = url.split('/')[-1]
        cmd = [
            'aria2c',
            '--console-log-level=error',
            '-c',
            '-x', '16',
            '-s', '16',
            '-k', '1M',
            '--file-allocation=none',
            '--optimize-concurrent-downloads=true',
            '--max-connection-per-server=16',
            '--min-split-size=1M',
            '--max-tries=5',
            '--retry-wait=10',
            '--connect-timeout=30',
            '--timeout=600',
            url,
            '-d', model_dir,
            '-o', filename
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"success": True, "message": "Download completed successfully"}
        else:
            return {"success": False, "message": f"Download failed: {result.stderr}"}
    except Exception as e:
        return {"success": False, "message": f"Error during download: {str(e)}"}

@app.route('/api/custom-nodes')
def api_custom_nodes():
    """API endpoint to get installed custom nodes"""
    return jsonify(get_installed_custom_nodes())

@app.route('/api/models')
def api_models():
    """API endpoint to get installed models"""
    return jsonify(get_installed_models())

@app.route('/logs')
def get_logs():
    return jsonify({'logs': get_current_logs()})

@app.route('/refresh_logs')
def refresh_logs():
    """Force a refresh of the logs. Useful when log file has been externally updated."""
    try:
        with log_lock:
            log_buffer.clear()
        
        # Reload logs from file
        log_file = os.path.join('logs', 'comfyui.log')
        if os.path.exists(log_file):
            with open(log_file, 'r') as file:
                content = file.readlines()
                processed_content = []
                
                # Keep only the last 500 lines and filter duplicates
                content = content[-500:] if len(content) > 500 else content
                prev_line = None
                for line in content:
                    stripped_line = line.strip()
                    if stripped_line and stripped_line != prev_line:
                        processed_content.append(stripped_line)
                    prev_line = stripped_line
                
                with log_lock:
                    log_buffer.extend(processed_content)
        
        socketio.emit('logs', {'logs': get_current_logs()})
        return jsonify({'success': True, 'message': 'Logs refreshed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error refreshing logs: {str(e)}'})

@app.route('/download/outputs')
def download_outputs():
    try:
        memory_file = create_output_zip()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'comfyui_outputs_{timestamp}.zip'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/civitai', methods=['POST'])
def download_civitai():
    data = request.get_json()
    url = data.get('url')
    api_key = data.get('api_key')
    model_type = data.get('model_type', 'loras')
    
    if not url:
        return jsonify({"success": False, "message": "URL is required"}), 400
    
    result = download_from_civitai(url, api_key, model_type)
    return jsonify(result)

@app.route('/download/huggingface', methods=['POST'])
def download_huggingface():
    data = request.get_json()
    url = data.get('url')
    model_type = data.get('model_type', 'loras')
    
    if not url:
        return jsonify({"success": False, "message": "URL is required"}), 400
    
    result = download_from_huggingface(url, model_type)
    return jsonify(result)

@app.route('/')
def index():
    logs = get_current_logs()
    
    # Get installed custom nodes and models
    custom_nodes = get_installed_custom_nodes()
    models = get_installed_models()
    
    # Count total models
    total_models = sum(len(models[category]) for category in models)
    
    # Detect if we're running in RunPod by checking environment variables
    is_runpod = 'RUNPOD_POD_ID' in os.environ
    
    # Get the RunPod proxy host and port
    if is_runpod:
        # In RunPod, we use the public FQDN provided by RunPod for the proxy
        # Format: https://{pod_id}-{port}.proxy.runpod.net
        pod_id = os.environ.get('RUNPOD_POD_ID', '')
        proxy_port = '8188'  # ComfyUI port
        proxy_host = f"{pod_id}-{proxy_port}.proxy.runpod.net"
        proxy_url = f"https://{proxy_host}"
    else:
        # For local development or other environments
        proxy_host = request.host.split(':')[0]
        proxy_port = '8188'
        proxy_url = f"http://{proxy_host}:{proxy_port}"
    
    response = make_response(render_template_string(HTML_TEMPLATE, 
                                                    logs=logs, 
                                                    proxy_url=proxy_url,
                                                    is_runpod=is_runpod,
                                                    custom_nodes=custom_nodes,
                                                    models=models,
                                                    total_models=total_models))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    print("Starting log monitoring thread...")
    log_thread = threading.Thread(target=tail_log_file, daemon=True)
    log_thread.start()
    
    print("Starting log viewer on port 8189...")
    socketio.run(app, 
                 host='0.0.0.0', 
                 port=8189, 
                 debug=False,
                 allow_unsafe_werkzeug=True)
