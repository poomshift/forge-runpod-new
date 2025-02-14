from flask import Flask, render_template_string, make_response, jsonify, send_file
import os
import psutil
import GPUtil
from datetime import datetime
import threading
import time
import subprocess
import signal
import sys
import platform
import zipfile
import io
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables to store stats and logs
system_stats = {
    'cpu': {
        'percent': 0, 
        'cores': [],
        'model': 'Unknown CPU',
        'frequency': 0
    },
    'memory': {'percent': 0, 'used': 0, 'total': 0},
    'gpu': {'name': 'N/A', 'percent': 0, 'memory_used': 0, 'memory_total': 0, 'temp': 0},
    'disk': {'percent': 0, 'used': 0, 'total': 0},
    'timestamp': ''
}

log_buffer = []
log_lock = threading.Lock()
comfyui_process = None

def get_cpu_info():
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0")
            model = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            winreg.CloseKey(key)
        else:
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if line.startswith('model name'):
                        model = line.split(':')[1].strip()
                        break
                else:
                    model = platform.processor()
    except:
        model = platform.processor() or "Unknown CPU"
    return model

def update_system_stats():
    # Get CPU model once at startup
    system_stats['cpu']['model'] = get_cpu_info()
    
    while True:
        try:
            # CPU stats
            system_stats['cpu']['percent'] = psutil.cpu_percent(interval=1)
            system_stats['cpu']['cores'] = psutil.cpu_percent(interval=1, percpu=True)
            system_stats['cpu']['frequency'] = psutil.cpu_freq().current if psutil.cpu_freq() else 0
            
            # Memory stats
            memory = psutil.virtual_memory()
            system_stats['memory']['percent'] = memory.percent
            system_stats['memory']['used'] = memory.used // (1024 * 1024 * 1024)  # Convert to GB
            system_stats['memory']['total'] = memory.total // (1024 * 1024 * 1024)  # Convert to GB
            
            # GPU stats
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]  # Get first GPU
                    system_stats['gpu'] = {
                        'name': gpu.name,
                        'percent': gpu.load * 100,
                        'memory_used': gpu.memoryUsed,
                        'memory_total': gpu.memoryTotal,
                        'temp': gpu.temperature
                    }
            except Exception:
                pass  # GPU info not available
            
            # Disk stats
            disk = psutil.disk_usage('/')
            system_stats['disk']['percent'] = disk.percent
            system_stats['disk']['used'] = disk.used // (1024 * 1024 * 1024)  # Convert to GB
            system_stats['disk']['total'] = disk.total // (1024 * 1024 * 1024)  # Convert to GB
            
            system_stats['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Emit system stats via WebSocket
            socketio.emit('system_stats', system_stats)
            
            time.sleep(2)  # Update every 2 seconds
        except Exception as e:
            print(f"Error updating system stats: {e}")
            time.sleep(5)  # Wait before retrying

def tail_log_file():
    """Continuously tail the log file and update the buffer"""
    log_file = os.path.join('logs', 'comfyui.log')
    
    if not os.path.exists(log_file):
        os.makedirs('logs', exist_ok=True)
        open(log_file, 'a').close()
    
    def follow(file):
        """Generator function that yields new lines in a file"""
        file.seek(0, 2)  # Go to the end of the file
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.1)  # Sleep briefly
                continue
            yield line

    try:
        with open(log_file, 'r') as file:
            # First, get existing content (last 500 lines)
            file.seek(0, 2)
            file_size = file.tell()
            block_size = 1024
            blocks = []
            
            while file_size > 0 and len(blocks) < 500:
                seek_size = min(file_size, block_size)
                file.seek(file_size - seek_size)
                blocks.insert(0, file.read(seek_size))
                file_size -= seek_size
            
            content = ''.join(blocks).splitlines()[-500:]
            with log_lock:
                log_buffer.extend(content)
                if len(log_buffer) > 500:
                    log_buffer[:] = log_buffer[-500:]
            
            # Emit initial logs
            socketio.emit('logs', {'logs': get_current_logs()})
            
            # Then follow the file for new content
            for line in follow(file):
                with log_lock:
                    log_buffer.append(line.strip())
                    if len(log_buffer) > 500:
                        log_buffer.pop(0)
                # Emit new log line via WebSocket
                socketio.emit('new_log_line', {'line': line.strip()})
    except Exception as e:
        print(f"Error tailing log file: {e}")
        time.sleep(5)

def get_current_logs():
    """Get the current logs with timestamp header"""
    with log_lock:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        header = f"Log Viewer - Last {len(log_buffer)} lines (as of {timestamp})\n"
        header += "=" * 80 + "\n\n"
        return header + '\n'.join(log_buffer)

def kill_comfyui():
    """Kill the ComfyUI process"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.cmdline())
                if 'python' in proc.name().lower() and 'main.py' in cmdline and 'ComfyUI' in cmdline:
                    proc.terminate()
                    proc.wait(timeout=5)  # Wait for process to terminate
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                continue
    except Exception as e:
        print(f"Error killing ComfyUI: {e}")
    return False

def start_comfyui():
    """Start the ComfyUI process"""
    global comfyui_process
    try:
        comfyui_dir = os.path.join('/workspace', 'ComfyUI')
        log_file = os.path.join('logs', 'comfyui.log')
        
        with open(log_file, 'a') as f:
            process = subprocess.Popen(
                [sys.executable, 'main.py', '--listen', '0.0.0.0', '--port', '8188'],
                cwd=comfyui_dir,
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True
            )
            comfyui_process = process
            return True
    except Exception as e:
        print(f"Error starting ComfyUI: {e}")
        return False

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

@app.route('/system_stats')
def get_system_stats():
    return jsonify(system_stats)

@app.route('/logs')
def get_logs():
    return jsonify({'logs': get_current_logs()})

@app.route('/control/kill')
def control_kill():
    success = kill_comfyui()
    return jsonify({'success': success})

@app.route('/control/start')
def control_start():
    success = start_comfyui()
    return jsonify({'success': success})

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

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>ComfyUI Control Center | Performance Monitor & Logs</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            /* Light theme variables */
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
            min-height: 0;  /* Important for scrolling */
        }
        
        .monitor-section {
            width: 400px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            overflow-y: auto;
        }
        
        .logs-section {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;  /* Important for text wrapping */
        }
        
        .card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: background-color 0.3s;
        }
        
        .card h2 {
            margin: 0 0 16px 0;
            font-size: 18px;
            color: var(--text-color);
        }
        
        .stat {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .stat-label {
            flex: 1;
            color: var(--text-secondary);
        }
        
        .stat-value {
            font-weight: 500;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: var(--progress-bg);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        
        .progress-fill {
            height: 100%;
            background: var(--primary-color);
            transition: width 0.3s ease;
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
        
        .interval-input {
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            width: 100px;
            font-size: 14px;
        }
        
        .status {
            color: var(--text-secondary);
            font-size: 14px;
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
        }
        
        .timestamp {
            color: var(--text-secondary);
            font-size: 12px;
            margin-top: 8px;
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
        
        /* Remove core usage styles */
        .core-usage {
            display: none;
        }
        
        .core {
            display: none;
        }
        
        .core-label {
            display: none;
        }
        
        .core-bar {
            display: none;
        }
        
        .core-fill {
            display: none;
        }
        
        .core-value {
            display: none;
        }

        /* Update CPU card to be more compact */
        .card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: background-color 0.3s;
        }

        /* Update JavaScript to remove core updates */
        function updateSystemStats() {
            fetch('/system_stats?t=' + new Date().getTime())
                .then(response => response.json())
                .then(stats => {
                    // Update CPU
                    document.getElementById('cpu-model').textContent = 
                        `${stats.cpu.model}${stats.cpu.frequency ? ` @ ${stats.cpu.frequency.toFixed(2)} MHz` : ''}`;
                    document.getElementById('cpu-usage').textContent = `${stats.cpu.percent.toFixed(1)}%`;
                    document.getElementById('cpu-bar').style.width = `${stats.cpu.percent}%`;
                    
                    // Update Memory
                    document.getElementById('memory-usage').textContent = 
                        `${stats.memory.used}GB / ${stats.memory.total}GB (${stats.memory.percent}%)`;
                    document.getElementById('memory-bar').style.width = `${stats.memory.percent}%`;
                    
                    // Update GPU
                    document.getElementById('gpu-name').textContent = stats.gpu.name;
                    document.getElementById('gpu-usage').textContent = 
                        `${stats.gpu.percent.toFixed(1)}% | ${stats.gpu.memory_used}MB / ${stats.gpu.memory_total}MB`;
                    document.getElementById('gpu-temp').textContent = `${stats.gpu.temp}°C`;
                    document.getElementById('gpu-bar').style.width = `${stats.gpu.percent}%`;
                    
                    // Update Disk
                    document.getElementById('disk-usage').textContent = 
                        `${stats.disk.used}GB / ${stats.disk.total}GB (${stats.disk.percent}%)`;
                    document.getElementById('disk-bar').style.width = `${stats.disk.percent}%`;
                    
                    // Update timestamp
                    document.getElementById('last-update').textContent = `Last updated: ${stats.timestamp}`;
                });
        }

        /* Update CPU card HTML */
        <div class="card">
            <h2>CPU Usage</h2>
            <div class="model-info" id="cpu-model">Unknown CPU</div>
            <div class="stat">
                <span class="stat-label">Total Usage</span>
                <span class="stat-value" id="cpu-usage">0%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="cpu-bar" style="width: 0%"></div>
            </div>
        </div>

        /* Theme switch styles */
        .theme-switch-wrapper {
            position: fixed;
            top: 20px;
            right: 30px;
            display: flex;
            align-items: center;
            gap: 8px;
            z-index: 1000;
            background: var(--card-bg);
            padding: 8px 16px;
            border-radius: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }

        .theme-switch-wrapper .icon {
            font-size: 20px;
            line-height: 1;
            user-select: none;
        }

        /* Auto-scroll control */
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

        /* Toggle switch styles */
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

        /* Process control buttons */
        .control-button {
            padding: 8px 16px;
            border-radius: 6px;
            border: none;
            cursor: pointer;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.3s ease;
            font-size: 14px;
        }

        .kill-button {
            background: #ef4444;
            color: white;
        }

        .kill-button:hover {
            background: #dc2626;
        }

        .start-button {
            background: #22c55e;
            color: white;
        }

        .start-button:hover {
            background: #16a34a;
        }

        .download-button {
            background: #8b5cf6;
            color: white;
        }

        .download-button:hover {
            background: #7c3aed;
        }

        .control-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .control-button .icon {
            font-size: 16px;
        }

        /* Update header controls style */
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

        /* Theme switch styles - updated for header */
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

        /* Remove the fixed position theme switch wrapper */
        .theme-switch-wrapper {
            display: none;
        }

        /* Update HTML structure in the header */
        <div class="header">
            <div class="title-section">
                <h1>ComfyUI Control Center</h1>
                <span class="title-badge">Performance Monitor & Logs</span>
            </div>
            <div class="controls">
                <div class="control-group">
                    <input type="number" id="refresh-interval" class="interval-input" 
                           min="1" placeholder="Seconds" 
                           onchange="startAutoRefresh()">
                    <span id="status" class="status"></span>
                </div>
                
                <div class="divider"></div>
                
                <div class="control-group">
                    <button id="kill-button" class="control-button kill-button" onclick="controlComfyUI('kill')">
                        <span class="icon">⚡</span> Kill ComfyUI
                    </button>
                    <button id="start-button" class="control-button start-button" onclick="controlComfyUI('start')">
                        <span class="icon">▶️</span> Start ComfyUI
                    </button>
                    <button id="download-button" class="control-button download-button" onclick="downloadOutputs()">
                        <span class="icon">📦</span> Download Outputs
                    </button>
                    
                    <div class="divider"></div>
                    
                    <div class="theme-switch">
                        <span id="theme-icon" class="icon">☀️</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="theme-toggle" onchange="toggleTheme()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
            </div>
        </div>

        /* Remove the old theme switch wrapper from body */
        <!-- Remove this from body:
        <div class="theme-switch-wrapper">
            <span id="theme-icon" class="icon">☀️</span>
            <label class="toggle-switch">
                <input type="checkbox" id="theme-toggle" onchange="toggleTheme()">
                <span class="toggle-slider"></span>
            </label>
        </div>
        -->
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        let socket;
        let refreshInterval;
        let autoScroll = true;
        let lastScrollPosition = 0;
        let userScrolled = false;

        // Add theme switching functionality
        function toggleTheme() {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            const themeToggle = document.getElementById('theme-toggle');
            
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Update icons
            document.getElementById('theme-icon').textContent = 
                newTheme === 'dark' ? '🌙' : '☀️';
            
            // Update checkbox state
            themeToggle.checked = newTheme === 'dark';
        }

        // Initialize theme
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
            
            // Handle system stats updates
            socket.on('system_stats', function(stats) {
                updateSystemStatsDisplay(stats);
            });
            
            // Handle new log lines
            socket.on('new_log_line', function(data) {
                appendLogLine(data.line);
            });
            
            // Handle complete log updates
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
            
            // Trim old logs if too many lines
            const maxLines = 500;
            let lines = logContainer.innerHTML.split('\\n');
            if (lines.length > maxLines) {
                lines = lines.slice(-maxLines);
                logContainer.innerHTML = lines.join('\\n');
            }
            
            if (autoScroll && !userScrolled) {
                scrollToBottom(logContainer);
            }
        }
        
        function updateSystemStatsDisplay(stats) {
            // Update CPU
            document.getElementById('cpu-model').textContent = 
                `${stats.cpu.model}${stats.cpu.frequency ? ` @ ${stats.cpu.frequency.toFixed(2)} MHz` : ''}`;
            document.getElementById('cpu-usage').textContent = `${stats.cpu.percent.toFixed(1)}%`;
            document.getElementById('cpu-bar').style.width = `${stats.cpu.percent}%`;
            
            // Update Memory
            document.getElementById('memory-usage').textContent = 
                `${stats.memory.used}GB / ${stats.memory.total}GB (${stats.memory.percent}%)`;
            document.getElementById('memory-bar').style.width = `${stats.memory.percent}%`;
            
            // Update GPU
            document.getElementById('gpu-name').textContent = stats.gpu.name;
            document.getElementById('gpu-usage').textContent = 
                `${stats.gpu.percent.toFixed(1)}% | ${stats.gpu.memory_used}MB / ${stats.gpu.memory_total}MB`;
            document.getElementById('gpu-temp').textContent = `${stats.gpu.temp}°C`;
            document.getElementById('gpu-bar').style.width = `${stats.gpu.percent}%`;
            
            // Update Disk
            document.getElementById('disk-usage').textContent = 
                `${stats.disk.used}GB / ${stats.disk.total}GB (${stats.disk.percent}%)`;
            document.getElementById('disk-bar').style.width = `${stats.disk.percent}%`;
            
            // Update timestamp
            document.getElementById('last-update').textContent = `Last updated: ${stats.timestamp}`;
        }
        
        function startAutoRefresh() {
            const seconds = parseInt(document.getElementById('refresh-interval').value);
            if (seconds < 1) {
                alert('Please enter a valid number of seconds (minimum 1)');
                return;
            }
            updateStatus(seconds);
        }
        
        function updateStatus(seconds) {
            document.getElementById('status').textContent = 
                `Auto-refreshing every ${seconds} seconds`;
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
        
        function controlComfyUI(action) {
            const killBtn = document.getElementById('kill-button');
            const startBtn = document.getElementById('start-button');
            
            // Disable both buttons during operation
            killBtn.disabled = true;
            startBtn.disabled = true;
            
            fetch(`/control/${action}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (action === 'kill') {
                            killBtn.disabled = true;
                            startBtn.disabled = false;
                        } else {
                            killBtn.disabled = false;
                            startBtn.disabled = true;
                        }
                    } else {
                        // Re-enable both buttons if operation failed
                        killBtn.disabled = false;
                        startBtn.disabled = false;
                        alert(`Failed to ${action} ComfyUI`);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    killBtn.disabled = false;
                    startBtn.disabled = false;
                    alert(`Error during ${action} operation`);
                });
        }
        
        function downloadOutputs() {
            const downloadBtn = document.getElementById('download-button');
            downloadBtn.disabled = true;
            
            // Create a temporary link element
            const link = document.createElement('a');
            link.href = '/download/outputs';
            link.target = '_blank';
            
            // Append to body, click, and remove
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Re-enable button after a short delay
            setTimeout(() => {
                downloadBtn.disabled = false;
            }, 2000);
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            initializeTheme();
            initializeWebSocket();
            
            const logContainer = document.getElementById('log-container');
            
            // Handle manual scrolling
            logContainer.addEventListener('scroll', function() {
                if (!isScrolledToBottom(logContainer)) {
                    userScrolled = true;
                } else {
                    userScrolled = false;
                }
            });
            
            // Initialize auto-refresh
            document.getElementById('refresh-interval').value = 5;
            startAutoRefresh();
            updateSystemStatsDisplay(system_stats);
            
            // Initial scroll to bottom
            scrollToBottom(logContainer);
        });
    </script>
</head>
<body>
    <div class="container">
    <div class="header">
            <div class="title-section">
                <h1>ComfyUI Control Center</h1>
                <span class="title-badge">Performance Monitor & Logs</span>
            </div>
            <div class="controls">
                <div class="control-group">
                    <input type="number" id="refresh-interval" class="interval-input" 
                           min="1" placeholder="Seconds" 
                           onchange="startAutoRefresh()">
                    <span id="status" class="status"></span>
                </div>
                
                <div class="divider"></div>
                
                <div class="control-group">
                    <button id="kill-button" class="control-button kill-button" onclick="controlComfyUI('kill')">
                        <span class="icon">⚡</span> Kill ComfyUI
                    </button>
                    <button id="start-button" class="control-button start-button" onclick="controlComfyUI('start')">
                        <span class="icon">▶️</span> Start ComfyUI
                    </button>
                    <button id="download-button" class="control-button download-button" onclick="downloadOutputs()">
                        <span class="icon">📦</span> Download Outputs
                    </button>
                    
                    <div class="divider"></div>
                    
                    <div class="theme-switch">
                        <span id="theme-icon" class="icon">☀️</span>
                        <label class="toggle-switch">
                            <input type="checkbox" id="theme-toggle" onchange="toggleTheme()">
                            <span class="toggle-slider"></span>
                        </label>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="main-content">
            <div class="monitor-section">
                <div class="card">
                    <h2>CPU Usage</h2>
                    <div class="model-info" id="cpu-model">Unknown CPU</div>
                    <div class="stat">
                        <span class="stat-label">Total Usage</span>
                        <span class="stat-value" id="cpu-usage">0%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-bar" style="width: 0%"></div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Memory Usage</h2>
                    <div class="stat">
                        <span class="stat-label">RAM Usage</span>
                        <span class="stat-value" id="memory-usage">0GB / 0GB (0%)</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-bar" style="width: 0%"></div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>GPU Status</h2>
                    <div class="stat">
                        <span class="stat-label">GPU Model</span>
                        <span class="stat-value" id="gpu-name">N/A</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Usage & Memory</span>
                        <span class="stat-value" id="gpu-usage">0% | 0MB / 0MB</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Temperature</span>
                        <span class="stat-value" id="gpu-temp">0°C</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="gpu-bar" style="width: 0%"></div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>Disk Usage</h2>
                    <div class="stat">
                        <span class="stat-label">Storage</span>
                        <span class="stat-value" id="disk-usage">0GB / 0GB (0%)</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="disk-bar" style="width: 0%"></div>
                    </div>
                </div>
                
                <div class="timestamp" id="last-update"></div>
            </div>
            
            <div class="logs-section">
                <div id="log-container">{{ logs }}</div>
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

@app.route('/')
def index():
    logs = get_current_logs()
    response = make_response(render_template_string(HTML_TEMPLATE, logs=logs))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    print("Starting system stats monitoring thread...")
    stats_thread = threading.Thread(target=update_system_stats, daemon=True)
    stats_thread.start()
    
    print("Starting log monitoring thread...")
    log_thread = threading.Thread(target=tail_log_file, daemon=True)
    log_thread.start()
    
    print("Starting log viewer on port 8189...")
    socketio.run(app, host='0.0.0.0', port=8189, debug=True)