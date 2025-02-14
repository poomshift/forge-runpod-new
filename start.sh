#!/bin/bash
mkdir -p /workspace/logs
touch /workspace/logs/comfyui.log

# Run updates if enabled
if [ "$UPDATE_ON_START" = "true" ]; then
    /workspace/update.sh
fi

# Download models
python3 /workspace/download_models.py

# Start Jupyter
jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8888 --NotebookApp.token="" --NotebookApp.password="" --notebook-dir=/workspace &

# Start ComfyUI
cd /workspace/ComfyUI
python main.py --listen 0.0.0.0 --port 8188 2>&1 | tee /workspace/logs/comfyui.log &

# Start log viewer
cd /workspace
python log_viewer.py &

# Wait for all processes
wait 