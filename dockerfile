FROM nvidia/cuda:12.4.0-base-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="${PATH}:/root/.local/bin:/root/.cargo/bin"

# Install system dependencies 
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    python3.10 \
    python3.10-venv \
    python3-pip \
    build-essential \
    libgl1-mesa-dev \
    libglib2.0-0 \
    wget \
    ffmpeg \
    aria2 \
    rsync \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory to root
WORKDIR /

# Install Jupyter and FastAPI dependencies with uv
RUN uv pip install \
    jupyter \
    jupyterlab \
    nodejs \
    opencv-python \
    requests \
    aiohttp \
    runpod \
    fastapi \
    "uvicorn[standard]" \
    websockets \
    pydantic \
    jinja2 \
    python-multipart \
    websocket-client \
    psutil \
    gputil \
    gdown

# Setup Jupyter configuration
RUN jupyter notebook --generate-config && \
    echo "c.NotebookApp.allow_root = True" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.ip = '0.0.0.0'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.token = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.password = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_origin = '*'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_remote_access = True" >> /root/.jupyter/jupyter_notebook_config.py

# Create workspace directory
RUN mkdir -p /workspace

# Copy scripts to root
WORKDIR /workspace
COPY . .

# Set environment variables for configuration
ENV UPDATE_ON_START=false \
    MODELS_CONFIG_URL="https://raw.githubusercontent.com/poomshift/comfyui-docker-new/refs/heads/main/models_config.json" \
    SKIP_MODEL_DOWNLOAD=false \
    FORCE_MODEL_DOWNLOAD=false

# Make scripts executable
RUN chmod +x *.sh ./download_models.py

# Expose ports
EXPOSE 8188 8888 8189

WORKDIR /

COPY start.sh .

RUN chmod +x *.sh

CMD ["./start.sh"]

