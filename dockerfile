FROM nvidia/cuda:12.8.0-devel-ubuntu22.04 as builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="${PATH}:/root/.local/bin"

# Install system dependencies
RUN apt-get update && apt-get install -y software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3.12 \
    python3.12-venv \
    python3-pip \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    wget \
    ffmpeg \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /workspace

# Clone ComfyUI and install dependencies
RUN git clone --depth=1 https://github.com/comfyanonymous/ComfyUI && \
    cd ComfyUI && \
    pip3 install --no-cache-dir torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu128 && \
    pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir jupyter jupyterlab nodejs opencv-python requests runpod flask flask-socketio websocket-client psutil gputil

# Create directory structure
RUN mkdir -p ComfyUI/models/{checkpoints,vae,unet,diffusion_models,text_encoders,loras} \
    ComfyUI/input \
    ComfyUI/output \
    logs

# Clone custom nodes and install requirements
WORKDIR /workspace/ComfyUI/custom_nodes
RUN git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Manager.git && \
    git clone --depth=1 https://github.com/cubiq/ComfyUI_essentials && \
    git clone --depth=1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-KJNodes && \
    git clone --depth=1 https://github.com/city96/ComfyUI-GGUF && \
    git clone --depth=1 https://github.com/ltdrdata/ComfyUI-Inspire-Pack && \
    git clone --depth=1 https://github.com/pythongosssss/ComfyUI-Custom-Scripts && \
    git clone --depth=1 https://github.com/rgthree/rgthree-comfy && \
    git clone --depth=1 https://github.com/facok/ComfyUI-TeaCacheHunyuanVideo && \
    git clone --depth=1 https://github.com/chengzeyi/Comfy-WaveSpeed && \
    git clone --depth=1 https://github.com/kijai/ComfyUI-HunyuanVideoWrapper && \
    find . -name "requirements.txt" -exec pip install --no-cache-dir -r {} \;

# Setup Jupyter configuration
RUN jupyter notebook --generate-config && \
    echo "c.NotebookApp.allow_root = True" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.ip = '0.0.0.0'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.token = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.password = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_origin = '*'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_remote_access = True" >> /root/.jupyter/jupyter_notebook_config.py

# Copy scripts
COPY download_models.py update.sh start.sh log_viewer.py /workspace/

# Set environment variables for configuration
ENV UPDATE_ON_START=false \
    MODELS_CONFIG_URL=https://huggingface.co/Patarapoom/model/resolve/main/models_config.json \
    SKIP_MODEL_DOWNLOAD=false \
    FORCE_MODEL_DOWNLOAD=false

# Make scripts executable
RUN chmod +x /workspace/*.sh /workspace/download_models.py

# Expose ports
EXPOSE 8188 8888 8189

WORKDIR /workspace
CMD ["./start.sh"]

