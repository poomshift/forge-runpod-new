#!/bin/bash
mkdir -p /workspace/logs
touch /workspace/logs/comfyui.log

# Run updates if enabled
if [ "$UPDATE_ON_START" = "true" ]; then
    /workspace/update.sh
fi

# Download models
python3 /workspace/download_models.py

# Install custom nodes
cd /workspace/ComfyUI/custom_nodes
git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager.git
git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials
git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
git clone --depth=1 https://github.com/kijai/ComfyUI-KJNodes
git clone --depth=1 https://github.com/city96/ComfyUI-GGUF
git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Inspire-Pack
git clone --depth=1 https://github.com/pythongosssss/ComfyUI-Custom-Scripts
git clone --depth=1 https://github.com/rgthree/rgthree-comfy
find . -name "requirements.txt" -exec pip install --no-cache-dir -r {} \;

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