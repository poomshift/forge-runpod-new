#!/bin/bash

# default environment variable

export UPDATE_ON_START=${UPDATE_ON_START:-"false"}
export MODELS_CONFIG_URL=${MODELS_CONFIG_URL:-"https://raw.githubusercontent.com/poomshift/forge-runpod-new/refs/heads/main/models_config.json"}
export SKIP_MODEL_DOWNLOAD=${SKIP_MODEL_DOWNLOAD:-"false"}
export FORCE_MODEL_DOWNLOAD=${FORCE_MODEL_DOWNLOAD:-"false"}
export LOG_PATH=${LOG_PATH:-"/notebooks/backend.log"}

export TORCH_FORCE_WEIGHTS_ONLY_LOAD=1

# Set strict error handling
set -e

# Function to check GPU availability with timeout
check_gpu() {
    local timeout=30
    local interval=2
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        if nvidia-smi >/dev/null 2>&1; then
            echo "GPU detected and ready"
            return 0
        fi
        sleep $interval
        elapsed=$((elapsed + interval))
        echo "Waiting for GPU... ($elapsed/$timeout seconds)"
    done

    echo "WARNING: GPU not detected after $timeout seconds"
    return 1
}

# Function to reset GPU state
reset_gpu() {
    echo "Resetting GPU state..."
    nvidia-smi --gpu-reset 2>/dev/null || true
    sleep 2
}

# Install uv if not already installed
install_uv() {
    if ! command -v uv &>/dev/null; then
        echo "Installing uv package installer..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    else
        echo "uv already installed, skipping..."
    fi
}

# Ensure CUDA environment is properly set
export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
export CUDA_LAUNCH_BLOCKING=1

# Create necessary directories
mkdir -p /workspace/logs

# Create log file if it doesn't exist
touch /workspace/logs/forge.log

# Clean up the log file to remove any duplicate lines
clean_log_file() {
    local log_file="/workspace/logs/forge.log"
    if [ -f "$log_file" ] && [ -s "$log_file" ]; then
        echo "Cleaning log file to remove duplicates..."
        awk '!seen[$0]++' "$log_file" >"${log_file}.tmp"
        mv "${log_file}.tmp" "$log_file"
    fi
}

# Clean the log file before starting the log viewer
clean_log_file

# Start log viewer early to monitor the installation process
cd /notebooks
# CUDA_VISIBLE_DEVICES="" python /log_viewer.py &
CUDA_VISIBLE_DEVICES="" nohup python /notebooks/log_viewer.py &>$LOG_PATH &
echo "Started log viewer on port 8189 - Monitor setup at http://localhost:8189"
cd /

# Install uv for faster package installation
install_uv

# Function to check internet connectivity
check_internet() {
    local max_attempts=5
    local attempt=1
    local timeout=5

    while [ $attempt -le $max_attempts ]; do
        echo "Checking internet connectivity (attempt $attempt/$max_attempts)..."
        if ping -c 1 -W $timeout 8.8.8.8 >/dev/null 2>&1; then
            echo "Internet connection is available."
            return 0
        fi
        echo "No internet connection. Waiting before retry..."
        sleep 10
        attempt=$((attempt + 1))
    done

    echo "WARNING: No internet connection after $max_attempts attempts."
    return 1
}

# Function to download config with retry
download_config() {
    local url=$1
    local output=$2
    local max_attempts=5
    local attempt=1
    local timeout=30

    while [ $attempt -le $max_attempts ]; do
        echo "Downloading config (attempt $attempt/$max_attempts)..."
        if wget --timeout=$timeout --tries=3 -O "$output" "$url" 2>/dev/null; then
            echo "Successfully downloaded config file."
            return 0
        fi
        echo "Download failed. Waiting before retry..."
        sleep 10
        attempt=$((attempt + 1))
    done

    echo "WARNING: Failed to download config after $max_attempts attempts."
    return 1
}

# Check for models_config.json and download it first thing
CONFIG_FILE="/workspace/models_config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating models_config.json..." | tee -a /workspace/logs/forge.log
    if [ -n "$MODELS_CONFIG_URL" ]; then
        if ! download_config "$MODELS_CONFIG_URL" "$CONFIG_FILE"; then
            echo "Failed to download from URL. Creating default config..." | tee -a /workspace/logs/forge.log
            echo '{
                "Stable-diffusion": [],
                "VAE": [],
                "Lora": [],
                "ESRGAN": [],
                "ControlNet": [],
                "text_encoder": []
            }' >"$CONFIG_FILE"
        fi
    else
        echo "No MODELS_CONFIG_URL provided. Creating default configuration..." | tee -a /workspace/logs/forge.log
        echo '{
            "Stable-diffusion": [],
            "VAE": [],
            "Lora": [],
            "ESRGAN": [],
            "ControlNet": [],
            "text_encoder": []
        }' >"$CONFIG_FILE"
    fi
else
    echo "models_config.json already exists, using existing file" | tee -a /workspace/logs/forge.log
fi

# Set Forge repo path
FORGE_PATH="/workspace/stable-diffusion-webui-forge"

# Clone Forge if not present
if [ ! -e "$FORGE_PATH/webui.py" ]; then
    echo "Stable Diffusion WebUI Forge not found, installing..."
    git clone --depth=1 https://github.com/lllyasviel/stable-diffusion-webui-forge "$FORGE_PATH"
fi

# Create Forge model directories
mkdir -p "$FORGE_PATH/models/Stable-diffusion"
mkdir -p "$FORGE_PATH/models/VAE"
mkdir -p "$FORGE_PATH/models/Lora"
mkdir -p "$FORGE_PATH/models/ESRGAN"
mkdir -p "$FORGE_PATH/models/ControlNet"
mkdir -p "$FORGE_PATH/models/text_encoder"

# Function to download a model if missing
download_model() {
    local url=$1
    local dest=$2
    local filename=$(basename "$url")
    if [ ! -f "$dest/$filename" ]; then
        echo "Downloading $filename to $dest..."
        wget -O "$dest/$filename" "$url"
    else
        echo "$filename already exists in $dest, skipping download."
    fi
}

# Download models as per models_config.json
CONFIG_FILE="/workspace/models_config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo "Processing models_config.json for Forge..."
    # Stable-diffusion (checkpoints)
    for url in $(jq -r '."Stable-diffusion"[]' "$CONFIG_FILE"); do
        download_model "$url" "$FORGE_PATH/models/Stable-diffusion"
    done
    # VAE
    for url in $(jq -r '.VAE[]' "$CONFIG_FILE"); do
        download_model "$url" "$FORGE_PATH/models/VAE"
    done
    # Lora
    for url in $(jq -r '.Lora[]' "$CONFIG_FILE"); do
        download_model "$url" "$FORGE_PATH/models/Lora"
    done
    # ESRGAN (upscale models)
    for url in $(jq -r '.ESRGAN[]' "$CONFIG_FILE"); do
        download_model "$url" "$FORGE_PATH/models/ESRGAN"
    done
    # ControlNet
    for url in $(jq -r '.ControlNet[]' "$CONFIG_FILE"); do
        download_model "$url" "$FORGE_PATH/models/ControlNet"
    done
    # text_encoder
    for url in $(jq -r '.text_encoder[]' "$CONFIG_FILE"); do
        download_model "$url" "$FORGE_PATH/models/text_encoder"
    done
fi

# Start Jupyter with GPU isolation
CUDA_VISIBLE_DEVICES="" jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8888 --NotebookApp.token="" --NotebookApp.password="" --notebook-dir=/workspace &

# Give other services time to initialize
sleep 5

# Start Forge with full GPU access
cd "$FORGE_PATH"
echo "===================================================================="
echo "============ Stable Diffusion WebUI Forge STARTING $(date) ============"
echo "===================================================================="
# Start Forge with proper logging
python launch.py --listen --port 7860 2>&1 | tee -a /workspace/logs/forge.log &
FORGE_PID=$!
echo "Forge started with PID: $FORGE_PID" | tee -a /workspace/logs/forge.log

# Wait for all processes
wait
