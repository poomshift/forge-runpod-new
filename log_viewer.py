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
import logging

# Initialize Flask and SocketIO with CORS
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Disable logging for frequent endpoints
class EndpointFilter(logging.Filter):
    def __init__(self, excluded_endpoints):
        self.excluded_endpoints = excluded_endpoints
        super().__init__()
        
    def filter(self, record):
        if hasattr(record, 'args') and len(record.args) >= 3:
            request_path = record.args[1]
            for endpoint in self.excluded_endpoints:
                if endpoint in request_path:
                    return False
        return True

# Apply the filter to the Werkzeug logger
logging.getLogger('werkzeug').addFilter(EndpointFilter(['/logs']))

# Global variables to store logs
log_buffer = []
log_lock = threading.Lock()

# Add HTML_TEMPLATE before the routes
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alchemist's ComfyUI</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb;
            --success: #10b981;
            --bg: #f9fafb;
            --card: #fff;
            --text: #222;
            --muted: #6b7280;
            --border: #e5e7eb;
            --radius: 10px;
            --shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        body {
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 0;
        }
        .wrap {
            max-width: 900px;
            margin: 32px auto;
            padding: 24px;
            background: var(--card);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
        }
        .title {
            font-size: 1.7rem;
            font-weight: 600;
            letter-spacing: -1px;
        }
        .controls {
            display: flex;
            gap: 12px;
        }
        .button {
            background: var(--primary);
            color: #fff;
            border: none;
            border-radius: 6px;
            padding: 8px 18px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
            text-decoration: none;
        }
        .button.secondary {
            background: #f3f4f6;
            color: var(--text);
            border: 1px solid var(--border);
        }
        .button.success {
            background: var(--success);
            color: #fff;
            border: none;
        }
        .button:active {
            background: #1e40af;
        }
        .section {
            margin-bottom: 32px;
        }
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .log-box {
            background: #f3f4f6;
            border-radius: var(--radius);
            padding: 18px;
            font-family: 'Fira Mono', 'Consolas', monospace;
            font-size: 0.98rem;
            color: #222;
            min-height: 220px;
            max-height: 350px;
            overflow-y: auto;
            border: 1px solid var(--border);
            transition: opacity 0.1s ease;
            white-space: pre-wrap;
            line-height: 1.5;
        }
        .log-box .progress {
            color: #10b981;
            font-weight: 500;
        }
        .log-box .info {
            color: #3b82f6;
        }
        .log-box .warning {
            color: #f59e0b;
        }
        .log-box .error {
            color: #ef4444;
        }
        .log-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            gap: 8px;
        }
        .log-source-toggle {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .auto-scroll-toggle {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.9rem;
            color: var(--muted);
        }
        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 36px;
            height: 20px;
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
            background-color: #ccc;
            transition: .3s;
            border-radius: 20px;
        }
        .toggle-slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 2px;
            bottom: 2px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }
        input:checked + .toggle-slider {
            background-color: var(--primary);
        }
        input:checked + .toggle-slider:before {
            transform: translateX(16px);
        }
        .downloaders {
            display: flex;
            flex-direction: column;
            background: #f3f4f6;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            overflow: hidden;
        }
        .downloader {
            flex: 1;
            padding: 18px 16px 12px 16px;
            display: none;
        }
        .downloader.active {
            display: block;
        }
        .downloader label {
            font-size: 0.97rem;
            color: var(--muted);
            margin-bottom: 4px;
            display: block;
        }
        .downloader input, .downloader select {
            width: 100%;
            padding: 7px 10px;
            margin-bottom: 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 1rem;
            background: #fff;
        }
        .downloader .button {
            width: 100%;
        }
        .tabs {
            display: flex;
            background: #e5e7eb;
            border-bottom: 1px solid var(--border);
        }
        .tab {
            padding: 12px 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            font-size: 0.95rem;
            text-align: center;
            flex: 1;
            border-right: 1px solid var(--border);
        }
        .tab:last-child {
            border-right: none;
        }
        .tab.active {
            background: #f3f4f6;
            border-bottom: 2px solid var(--primary);
            margin-bottom: -1px;
        }
        .status-message {
            margin-top: 10px;
            font-size: 0.97rem;
            border-radius: 6px;
            padding: 8px 10px;
            display: none;
        }
        .status-success {
            background: #dcfce7;
            color: #166534;
            display: block;
        }
        .status-error {
            background: #fee2e2;
            color: #991b1b;
            display: block;
        }
        .collapsible {
            background: #f3f4f6;
            border-radius: var(--radius);
            margin-bottom: 16px;
            border: 1px solid var(--border);
            overflow: hidden;
        }
        .collapsible-header {
            padding: 12px 16px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #f9fafb;
        }
        .collapsible-content {
            padding: 0;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease, padding 0.3s ease;
        }
        .collapsible.open .collapsible-content {
            padding: 16px;
            max-height: 300px;
            overflow-y: auto;
        }
        .model-list, .node-list {
            margin: 0;
            padding: 0;
            list-style: none;
        }
        .model-list li, .node-list li {
            padding: 6px 0;
            border-bottom: 1px solid var(--border);
            font-size: 0.9rem;
        }
        .model-list li:last-child, .node-list li:last-child {
            border-bottom: none;
        }
        .category-name {
            font-weight: 600;
            margin: 12px 0 8px 0;
            padding-bottom: 4px;
            border-bottom: 1px solid var(--border);
        }
        .toggle-icon {
            transition: transform 0.3s ease;
        }
        .collapsible.open .toggle-icon {
            transform: rotate(180deg);
        }
        @media (max-width: 700px) {
            .wrap { padding: 8px; }
            .downloaders { flex-direction: column; gap: 16px; }
        }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        let socket;
        let lastLogHash = '';
        let logUpdateCounter = 0;
        let isUpdating = false;
        let autoScroll = true;
        let userScrolled = false;
        let useContainerLogs = false;
        
        function initializeWebSocket() {
            try {
                socket = io();
                socket.on('connect', function() {
                    console.log('WebSocket connected');
                });
                socket.on('new_log_line', function(data) {
                    console.log('New log line received via WebSocket');
                    fetchLatestLogs(false);
                });
                socket.on('logs', function(data) {
                    console.log('Full logs received via WebSocket');
                    updateLogBoxSmoothly(data.logs);
                });
            } catch (e) {
                console.error('WebSocket initialization failed:', e);
            }
        }
        
        function processLogLine(line) {
            // Replace ANSI color codes with HTML spans for styling
            const colorMap = {
                '0;30': 'color: #000000;', // Black
                '0;31': 'color: #ef4444;', // Red
                '0;32': 'color: #10b981;', // Green
                '0;33': 'color: #f59e0b;', // Yellow
                '0;34': 'color: #3b82f6;', // Blue
                '0;35': 'color: #a855f7;', // Magenta
                '0;36': 'color: #06b6d4;', // Cyan
                '0;37': 'color: #9ca3af;', // White
                '1;30': 'color: #4b5563; font-weight: bold;', // Bright Black
                '1;31': 'color: #dc2626; font-weight: bold;', // Bright Red
                '1;32': 'color: #059669; font-weight: bold;', // Bright Green
                '1;33': 'color: #d97706; font-weight: bold;', // Bright Yellow
                '1;34': 'color: #2563eb; font-weight: bold;', // Bright Blue
                '1;35': 'color: #7c3aed; font-weight: bold;', // Bright Magenta
                '1;36': 'color: #0891b2; font-weight: bold;', // Bright Cyan
                '1;37': 'color: #f3f4f6; font-weight: bold;', // Bright White
            };
            
            // Function to escape HTML special characters
            function escapeHtml(text) {
                return text
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }
            
            // Escape HTML in the line
            let processedLine = escapeHtml(line);
            
            // Process progress indicators (lines with percentages)
            if (processedLine.match(/\d+%/) && processedLine.includes('|')) {
                return `<span class="progress">${processedLine}</span>`;
            }
            
            // Process INFO/WARNING/ERROR tags
            if (processedLine.includes('INFO')) {
                return `<span class="info">${processedLine}</span>`;
            }
            if (processedLine.includes('WARNING') || processedLine.includes('UserWarning')) {
                return `<span class="warning">${processedLine}</span>`;
            }
            if (processedLine.includes('ERROR')) {
                return `<span class="error">${processedLine}</span>`;
            }
            
            // Return the processed line
            return processedLine;
        }
        
        function updateLogBoxSmoothly(logs) {
            if (!logs || isUpdating) return;
            
            const logBox = document.getElementById('log-box');
            
            // Generate simple hash of the log content to check for changes
            const hash = String(logs).length + '-' + String(logs).substr(0, 50);
            if (hash !== lastLogHash) {
                // Only update if content actually changed
                isUpdating = true;
                
                // Save current scroll position and check if scrolled to bottom
                const wasAtBottom = isScrolledToBottom(logBox) || (autoScroll && !userScrolled);
                const scrollPos = logBox.scrollTop;
                
                // Update content with minimal flickering
                requestAnimationFrame(() => {
                    logBox.style.opacity = '0.7';
                    
                    // Use timeout to allow the opacity transition to happen
                    setTimeout(() => {
                        // Process log lines with HTML formatting
                        const processedLogs = logs.split('\n').map(line => {
                            return processLogLine(line);
                        }).join('\n');
                        
                        logBox.innerHTML = processedLogs;
                        logBox.style.opacity = '1';
                        
                        // Maintain scroll position
                        if (wasAtBottom) {
                            scrollToBottom(logBox);
                        } else {
                            logBox.scrollTop = scrollPos;
                        }
                        
                        console.log('Log content updated (' + (++logUpdateCounter) + ')');
                        lastLogHash = hash;
                        isUpdating = false;
                    }, 50);
                });
            }
        }
        
        function isScrolledToBottom(element) {
            return Math.abs(element.scrollHeight - element.scrollTop - element.clientHeight) < 1;
        }
        
        function scrollToBottom(element) {
            element.scrollTop = element.scrollHeight;
        }
        
        function toggleAutoScroll() {
            autoScroll = !autoScroll;
            userScrolled = false;
            
            // If turning on auto-scroll, immediately scroll to bottom
            if (autoScroll) {
                const logBox = document.getElementById('log-box');
                scrollToBottom(logBox);
            }
            
            // Save preference
            localStorage.setItem('autoScroll', autoScroll ? 'true' : 'false');
            console.log('Auto-scroll ' + (autoScroll ? 'enabled' : 'disabled'));
        }
        
        function forceRefreshLogs() {
            console.log('Forcing log refresh...');
            const logBox = document.getElementById('log-box');
            
            // Visual indication that refresh is happening
            logBox.style.opacity = '0.5';
            
            fetch('/refresh_logs', { 
                method: 'GET',
                cache: 'no-cache'
            })
            .then(response => response.json())
            .then(data => {
                console.log('Refresh complete, fetching latest logs');
                fetchLatestLogs(true);
            })
            .catch(error => {
                console.error('Error refreshing logs:', error);
                logBox.style.opacity = '1';
                fetchLatestLogs(true);
            });
        }
        
        function toggleContainerLogs() {
            useContainerLogs = !useContainerLogs;
            forceRefreshLogs();
            localStorage.setItem('useContainerLogs', useContainerLogs ? 'true' : 'false');
            console.log('Container logs ' + (useContainerLogs ? 'enabled' : 'disabled'));
        }
        
        function fetchLatestLogs(isManualRefresh) {
            if (isUpdating && !isManualRefresh) return;
            
            console.log('Fetching latest logs...');
            const endpoint = useContainerLogs ? '/container_logs' : '/logs';
            
            fetch(endpoint, { 
                method: 'GET',
                cache: 'no-cache',
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data && data.logs) {
                    console.log('Latest logs received, updating display');
                    updateLogBoxSmoothly(data.logs);
                } else {
                    console.warn('No logs data in response');
                    document.getElementById('log-box').style.opacity = '1';
                }
            })
            .catch(error => {
                console.error('Error fetching logs:', error);
                document.getElementById('log-box').style.opacity = '1';
            });
        }
        
        // Auto-poll for logs every 3 seconds
        function startAutoPoll() {
            console.log('Starting auto polling');
            setInterval(() => fetchLatestLogs(false), 3000);
        }
        
        function downloadFromCivitai() {
            const url = document.getElementById('modelUrl').value;
            const apiKey = document.getElementById('apiKey').value;
            const modelType = document.getElementById('modelType').value;
            const statusDiv = document.getElementById('downloadStatus');
            statusDiv.className = 'status-message';
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Downloading...';
            fetch('/download/civitai', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, api_key: apiKey, model_type: modelType })
            })
            .then(response => response.json())
            .then(data => {
                statusDiv.textContent = data.message;
                statusDiv.className = data.success ? 'status-message status-success' : 'status-message status-error';
            })
            .catch(error => {
                statusDiv.textContent = 'Error: ' + error.message;
                statusDiv.className = 'status-message status-error';
            });
        }
        
        function downloadFromHuggingFace() {
            const url = document.getElementById('hfUrl').value;
            const modelType = document.getElementById('hfModelType').value;
            const statusDiv = document.getElementById('hfDownloadStatus');
            statusDiv.className = 'status-message';
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Downloading...';
            fetch('/download/huggingface', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, model_type: modelType })
            })
            .then(response => response.json())
            .then(data => {
                statusDiv.textContent = data.message;
                statusDiv.className = data.success ? 'status-message status-success' : 'status-message status-error';
            })
            .catch(error => {
                statusDiv.textContent = 'Error: ' + error.message;
                statusDiv.className = 'status-message status-error';
            });
        }
        
        function downloadFromGoogleDrive() {
            const url = document.getElementById('gdUrl').value;
            const modelType = document.getElementById('gdModelType').value;
            const filename = document.getElementById('gdFilename').value;
            const statusDiv = document.getElementById('gdDownloadStatus');
            
            statusDiv.className = 'status-message';
            statusDiv.style.display = 'block';
            statusDiv.textContent = 'Downloading...';
            
            fetch('/download/googledrive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    url: url, 
                    model_type: modelType,
                    filename: filename
                })
            })
            .then(response => response.json())
            .then(data => {
                statusDiv.textContent = data.message;
                statusDiv.className = data.success ? 'status-message status-success' : 'status-message status-error';
            })
            .catch(error => {
                statusDiv.textContent = 'Error: ' + error.message;
                statusDiv.className = 'status-message status-error';
            });
        }
        
        function switchTab(tabName) {
            // Hide all downloaders
            document.querySelectorAll('.downloader').forEach(downloader => {
                downloader.classList.remove('active');
            });
            
            // Deactivate all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Activate the selected tab and downloader
            document.getElementById(tabName + '-tab').classList.add('active');
            document.getElementById(tabName + '-downloader').classList.add('active');
        }
        
        function toggleCollapsible(element) {
            element.classList.toggle('open');
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Page loaded, initializing systems');
            
            // Initialize WebSocket and fallback polling
            initializeWebSocket();
            
            // Set up container logs toggle from saved preference
            const savedContainerLogs = localStorage.getItem('useContainerLogs');
            if (savedContainerLogs !== null) {
                useContainerLogs = savedContainerLogs === 'true';
                document.getElementById('container-log-toggle').checked = useContainerLogs;
            }
            
            // Immediately fetch logs on page load
            fetchLatestLogs();
            
            // Start auto-polling
            startAutoPoll();
            
            // Make the Refresh Logs button call our enhanced function
            document.getElementById('refresh-logs-btn').addEventListener('click', forceRefreshLogs);
            
            // Initialize collapsible sections - fixed implementation
            document.querySelectorAll('.collapsible').forEach(function(collapsible) {
                const header = collapsible.querySelector('.collapsible-header');
                header.addEventListener('click', function() {
                    collapsible.classList.toggle('open');
                });
            });
            
            // Initialize tabs - start with Civitai tab active
            document.querySelectorAll('.tab').forEach(function(tab) {
                tab.addEventListener('click', function() {
                    const tabName = this.id.replace('-tab', '');
                    switchTab(tabName);
                });
            });
            switchTab('civitai');
            
            // Set up auto-scroll toggle from saved preference
            const savedAutoScroll = localStorage.getItem('autoScroll');
            if (savedAutoScroll !== null) {
                autoScroll = savedAutoScroll === 'true';
                document.getElementById('auto-scroll-toggle').checked = autoScroll;
            }
            
            // Add scroll listener to detect when user manually scrolls
            const logBox = document.getElementById('log-box');
            logBox.addEventListener('scroll', function() {
                // Only mark as user scrolled if auto-scroll is on and they scroll up
                if (autoScroll && !isScrolledToBottom(logBox)) {
                    userScrolled = true;
                }
                
                // If they scroll to bottom, reset userScrolled
                if (isScrolledToBottom(logBox)) {
                    userScrolled = false;
                }
            });
        });
    </script>
</head>
<body>
    <div class="wrap">
        <header>
            <div class="title">Alchemist's ComfyUI</div>
            <div class="controls">
                <a href="{{ proxy_url }}" target="_blank" class="button success">Open ComfyUI</a>
                <button id="refresh-logs-btn" class="button">Refresh Logs</button>
                <a href="/download/outputs" class="button">Download Outputs</a>
            </div>
        </header>
        
        <div class="section">
            <div class="section-title">Pre-installed</div>
            
            <div class="collapsible">
                <div class="collapsible-header">
                    <span>Custom Nodes ({{ custom_nodes|length }})</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="collapsible-content">
                    <ul class="node-list">
                        {% if custom_nodes %}
                            {% for node in custom_nodes %}
                                <li>{{ node.name }}</li>
                            {% endfor %}
                        {% else %}
                            <li>No custom nodes installed</li>
                        {% endif %}
                    </ul>
                </div>
            </div>
            
            <div class="collapsible">
                <div class="collapsible-header">
                    <span>Installed Models ({{ total_models }})</span>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="collapsible-content">
                    {% if models %}
                        {% for category, items in models.items() %}
                            {% if items %}
                                <div class="category-name">{{ category }} ({{ items|length }})</div>
                                <ul class="model-list">
                                    {% for model in items %}
                                        <li>{{ model.name }}</li>
                                    {% endfor %}
                                </ul>
                            {% endif %}
                        {% endfor %}
                    {% else %}
                        <p>No models found</p>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">Logs</div>
            <div class="log-controls">
                <div class="log-source-toggle">
                    <label class="toggle-switch">
                        <input type="checkbox" id="container-log-toggle" onchange="toggleContainerLogs()">
                        <span class="toggle-slider"></span>
                    </label>
                    <span>Show Container Logs</span>
                </div>
                <div class="auto-scroll-toggle">
                    <span>Auto-scroll</span>
                    <label class="toggle-switch">
                        <input type="checkbox" id="auto-scroll-toggle" checked onchange="toggleAutoScroll()">
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            </div>
            <div id="log-box" class="log-box">{{ logs }}</div>
        </div>
        
        <div class="section">
            <div class="section-title">Model Downloaders</div>
            <div class="downloaders">
                <div class="tabs">
                    <div id="civitai-tab" class="tab" onclick="switchTab('civitai')">Civitai</div>
                    <div id="huggingface-tab" class="tab" onclick="switchTab('huggingface')">Hugging Face</div>
                    <div id="googledrive-tab" class="tab" onclick="switchTab('googledrive')">Google Drive</div>
                </div>
                
                <div id="civitai-downloader" class="downloader">
                    <div style="font-weight:600;margin-bottom:8px;">Civitai Downloader</div>
                    <label for="modelUrl">Model URL</label>
                    <input type="url" id="modelUrl" placeholder="https://civitai.com/api/download/models/1399707" required>
                    <label for="apiKey">API Key (Optional)</label>
                    <input type="text" id="apiKey" placeholder="Your Civitai API key">
                    <label for="modelType">Model Type</label>
                    <select id="modelType">
                        <option value="models/checkpoints">Checkpoints</option>
                        <option value="models/vae">VAE</option>
                        <option value="models/unet">UNet</option>
                        <option value="models/diffusion_models">Diffusion Models</option>
                        <option value="models/text_encoders">Text Encoders</option>
                        <option value="models/loras">LORAs</option>
                        <option value="models/upscale_models">Upscale Models</option>
                        <option value="models/clip">CLIP</option>
                        <option value="models/controlnet">ControlNet</option>
                        <option value="models/clip_vision">CLIP Vision</option>
                        <option value="models/ipadapter">IPAdapter</option>
                    </select>
                    <button onclick="downloadFromCivitai()" class="button">Download Model</button>
                    <div id="downloadStatus" class="status-message"></div>
                </div>
                
                <div id="huggingface-downloader" class="downloader">
                    <div style="font-weight:600;margin-bottom:8px;">Hugging Face Downloader</div>
                    <label for="hfUrl">Model URL</label>
                    <input type="url" id="hfUrl" placeholder="https://huggingface.co/[user]/[repo]/resolve/main/model.safetensors" required>
                    <label for="hfModelType">Model Type</label>
                    <select id="hfModelType">
                        <option value="models/checkpoints">Checkpoints</option>
                        <option value="models/vae">VAE</option>
                        <option value="models/unet">UNet</option>
                        <option value="models/diffusion_models">Diffusion Models</option>
                        <option value="models/text_encoders">Text Encoders</option>
                        <option value="models/loras">LORAs</option>
                        <option value="models/upscale_models">Upscale Models</option>
                        <option value="models/clip">CLIP</option>
                        <option value="models/controlnet">ControlNet</option>
                        <option value="models/clip_vision">CLIP Vision</option>
                        <option value="models/ipadapter">IPAdapter</option>
                    </select>
                    <button onclick="downloadFromHuggingFace()" class="button">Download Model</button>
                    <div id="hfDownloadStatus" class="status-message"></div>
                </div>
                
                <div id="googledrive-downloader" class="downloader">
                    <div style="font-weight:600;margin-bottom:8px;">Google Drive Downloader</div>
                    <label for="gdUrl">Google Drive URL or ID</label>
                    <input type="text" id="gdUrl" placeholder="https://drive.google.com/file/d/FILEID/view or just FILEID" required>
                    <label for="gdModelType">Model Type</label>
                    <select id="gdModelType">
                        <option value="models/checkpoints">Checkpoints</option>
                        <option value="models/vae">VAE</option>
                        <option value="models/unet">UNet</option>
                        <option value="models/diffusion_models">Diffusion Models</option>
                        <option value="models/text_encoders">Text Encoders</option>
                        <option value="models/loras">LORAs</option>
                        <option value="models/upscale_models">Upscale Models</option>
                        <option value="models/clip">CLIP</option>
                        <option value="models/controlnet">ControlNet</option>
                        <option value="models/clip_vision">CLIP Vision</option>
                        <option value="models/ipadapter">IPAdapter</option>
                    </select>
                    <label for="gdFilename">Filename (Optional)</label>
                    <input type="text" id="gdFilename" placeholder="Leave empty to use original filename">
                    <button onclick="downloadFromGoogleDrive()" class="button">Download Model</button>
                    <div id="gdDownloadStatus" class="status-message"></div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

def get_installed_custom_nodes():
    """Get a list of installed custom nodes from start.sh"""
    custom_nodes = []
    
    try:
        # Check multiple possible locations for start.sh
        start_sh_paths = ['/start.sh', './start.sh', '/workspace/start.sh', os.path.join(os.path.dirname(__file__), 'start.sh')]
        start_sh_content = None
        
        for path in start_sh_paths:
            if os.path.exists(path):
                with open(path, 'r') as file:
                    start_sh_content = file.read()
                break
        
        if not start_sh_content:
            print("Warning: start.sh not found in expected locations")
            return []
            
        # Extract git clone lines for custom nodes
        import re
        pattern = r'git clone --depth=1 (https://github.com/[^/]+/([^\.]+)\.git)'
        matches = re.findall(pattern, start_sh_content)
        
        for match in matches:
            repo_url, repo_name = match
            # Extract the actual repository name from the URL
            repo_name_clean = repo_url.split('/')[-1].replace('.git', '')
            
            custom_nodes.append({
                'name': repo_name_clean,
                'path': f"/workspace/ComfyUI/custom_nodes/{repo_name_clean}",
                'version': "Installed",
                'url': repo_url
            })
    except Exception as e:
        print(f"Error parsing custom nodes from start.sh: {e}")
    
    # Sort alphabetically
    return sorted(custom_nodes, key=lambda x: x['name'].lower())

def get_installed_models():
    """Get a list of installed models from models_config.json"""
    models = {}
    
    try:
        # Check multiple possible locations for models_config.json
        config_paths = [
            '/workspace/models_config.json', 
            './models_config.json',
            os.path.join(os.path.dirname(__file__), 'models_config.json')
        ]
        
        model_config = None
        for path in config_paths:
            if os.path.exists(path):
                import json
                with open(path, 'r') as file:
                    model_config = json.load(file)
                break
        
        if not model_config:
            print("Warning: models_config.json not found in expected locations")
            return {}
        
        # Process each model category
        for category, urls in model_config.items():
            if urls:  # Only process non-empty categories
                model_files = []
                for url in urls:
                    # Extract filename from URL
                    filename = url.split('/')[-1]
                    # Add model information
                    model_files.append({
                        'name': filename,
                        'path': f"/workspace/ComfyUI/models/{category}/{filename}",
                        'size': "From config",
                        'url': url
                    })
                
                if model_files:
                    # Sort by name
                    model_files.sort(key=lambda x: x['name'].lower())
                    models[category] = model_files
    except Exception as e:
        print(f"Error parsing models from models_config.json: {e}")
    
    # Sort categories alphabetically
    return dict(sorted(models.items()))

def get_current_logs():
    """Get the current logs from the buffer"""
    with log_lock:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"Log Viewer - Last {len(log_buffer)} lines (as of {timestamp})\n"
        header += "=" * 80 + "\n\n"
        
        # Return log buffer with proper formatting
        if log_buffer:
            return header + '\n'.join(log_buffer)
        else:
            return header + "No logs yet."

def tail_log_file():
    """Continuously tail the log file and update the buffer"""
    log_file = os.path.join('logs', 'comfyui.log')
    
    if not os.path.exists(log_file):
        os.makedirs('logs', exist_ok=True)
        open(log_file, 'a').close()
        print(f"Created new log file at {log_file}")
    else:
        print(f"Found existing log file at {log_file}")
    
    def follow(file_path):
        """Generator function that yields new lines in a file with proper handling of file rotation/truncation"""
        print(f"Starting to follow log file: {file_path}")
        current_position = 0
        current_inode = os.stat(file_path).st_ino if os.path.exists(file_path) else None
        
        while True:
            try:
                # Check if file exists
                if not os.path.exists(file_path):
                    print(f"Log file does not exist: {file_path}, waiting...")
                    time.sleep(1)
                    continue
                
                # Check if file has been rotated (different inode)
                try:
                    new_inode = os.stat(file_path).st_ino
                    if current_inode is not None and new_inode != current_inode:
                        print(f"Log file rotated (inode changed: {current_inode} -> {new_inode})")
                        current_position = 0
                        current_inode = new_inode
                except Exception as e:
                    print(f"Error checking file inode: {e}")
                
                # Open file and read new content
                with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                    # Check if file has been truncated
                    file_size = os.path.getsize(file_path)
                    if file_size < current_position:
                        print(f"Log file truncated (size: {file_size}, previous position: {current_position})")
                        current_position = 0  # File was truncated, start from beginning
                    
                    # Seek to last position
                    file.seek(current_position)
                    
                    # Read raw content to handle progress bars with \r
                    raw_content = file.read(file_size - current_position)
                    if raw_content:
                        current_position = file.tell()
                        
                        # Split by both newlines and carriage returns to capture progress updates
                        lines = []
                        for part in raw_content.split('\n'):
                            # Handle carriage returns which are used for progress bars
                            cr_parts = part.split('\r')
                            # Add all parts except empty ones
                            lines.extend([p for p in cr_parts if p.strip()])
                        
                        print(f"Read {len(lines)} new content parts, position now at {current_position}")
                        for line in lines:
                            yield line
                    else:
                        # No new content, sleep before checking again
                        time.sleep(0.1)
            except Exception as e:
                print(f"Error following log file: {e}")
                time.sleep(1)  # Wait a bit longer on error

    try:
        # Load initial content
        print("Loading initial log content...")
        with open(log_file, 'r', encoding='utf-8', errors='replace') as file:
            content = file.read()
            
            # Process content to handle both newlines and carriage returns
            processed_content = []
            for part in content.split('\n'):
                # Handle carriage returns which are used for progress bars
                cr_parts = part.split('\r')
                # Add all non-empty parts
                processed_content.extend([p.strip() for p in cr_parts if p.strip()])
            
            # Keep only the last 500 lines and filter duplicates
            processed_content = processed_content[-500:] if len(processed_content) > 500 else processed_content
            
            # Remove consecutive duplicates
            filtered_content = []
            prev_line = None
            for line in processed_content:
                if line != prev_line:
                    filtered_content.append(line)
                prev_line = line
            
            with log_lock:
                log_buffer.clear()
                log_buffer.extend(filtered_content)
            
            print(f"Loaded {len(filtered_content)} initial log lines")
            # Emit initial logs
            socketio.emit('logs', {'logs': get_current_logs()})
        
        # Start the continuous tail
        print("Starting continuous log monitoring...")
        prev_line = None
        for line in follow(log_file):
            stripped_line = line.strip()
            if stripped_line:  # Only process non-empty lines
                with log_lock:
                    # Only add if different from the last line (avoid duplicates from progress updates)
                    if stripped_line != prev_line:
                        log_buffer.append(stripped_line)
                        if len(log_buffer) > 500:
                            log_buffer.pop(0)
                        # Emit new log line via WebSocket
                        socketio.emit('new_log_line', {'line': stripped_line})
                prev_line = stripped_line
    except Exception as e:
        print(f"Error tailing log file: {e}")
        time.sleep(5)
        # Try to restart the log monitoring
        tail_log_file()

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
    # Handle model_type with or without 'models/' prefix
    if model_type.startswith('models/'):
        model_path = model_type
    else:
        model_path = os.path.join('models', model_type)
    
    model_dir = os.path.join('/workspace', 'ComfyUI', model_path)
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
    # Handle model_type with or without 'models/' prefix
    if model_type.startswith('models/'):
        model_path = model_type
    else:
        model_path = os.path.join('models', model_type)
    
    model_dir = os.path.join('/workspace', 'ComfyUI', model_path)
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

def download_from_googledrive(url, model_type="loras", custom_filename=None):
    """Download a model from Google Drive using gdown"""
    # Handle model_type with or without 'models/' prefix
    if model_type.startswith('models/'):
        model_path = model_type
    else:
        model_path = os.path.join('models', model_type)
    
    model_dir = os.path.join('/workspace', 'ComfyUI', model_path)
    os.makedirs(model_dir, exist_ok=True)
    
    try:
        # Extract file ID from URL if it's a full URL
        file_id = url
        if 'drive.google.com' in url:
            if '/file/d/' in url:
                file_id = url.split('/file/d/')[1].split('/')[0]
            elif 'id=' in url:
                file_id = url.split('id=')[1].split('&')[0]
        
        # Set output path
        output_path = os.path.join(model_dir, custom_filename) if custom_filename else model_dir
        
        # Check if gdown is installed, if not install it
        try:
            subprocess.run(['pip', 'show', 'gdown'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            subprocess.run(['pip', 'install', 'gdown'], check=True)
        
        # Download the file
        if custom_filename:
            cmd = ['gdown', '--id', file_id, '-O', os.path.join(model_dir, custom_filename)]
        else:
            cmd = ['gdown', '--id', file_id, '-O', model_dir]
        
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

@app.route('/download/googledrive', methods=['POST'])
def download_googledrive():
    data = request.get_json()
    url = data.get('url')
    model_type = data.get('model_type', 'loras')
    filename = data.get('filename')
    
    if not url:
        return jsonify({"success": False, "message": "URL is required"}), 400
    
    # Use custom filename only if provided
    custom_filename = filename if filename and filename.strip() else None
    
    result = download_from_googledrive(url, model_type, custom_filename)
    return jsonify(result)

@app.route('/container_logs')
def get_container_logs():
    """Get logs directly from the container"""
    try:
        # Use subprocess to get the container logs
        cmd = ["docker", "logs", "--tail", "500", "$(hostname)"]
        
        try:
            # Try docker first
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            logs = result.stdout
        except:
            # If docker fails, try reading from system journal
            try:
                result = subprocess.run(["journalctl", "-n", "500"], capture_output=True, text=True)
                logs = result.stdout
            except:
                # Last resort: try to get logs from stdout/stderr files
                logs = "Could not access container logs directly."
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"Container Logs - Last 500 lines (as of {timestamp})\n"
        header += "=" * 80 + "\n\n"
        
        return jsonify({'logs': header + logs})
    except Exception as e:
        return jsonify({'logs': f"Error fetching container logs: {str(e)}"})

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
                 log_output=False,
                 allow_unsafe_werkzeug=True)

