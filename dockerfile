FROM nvidia/cuda:12.1.0-base-ubuntu22.04 AS builder

ARG PYTHON_VERSION="3.10"
ARG CONTAINER_TIMEZONE=UTC 

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="${PATH}:/root/.local/bin:/root/.cargo/bin"

# Install system dependencies 
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    git \
    build-essential \
    libgl1-mesa-dev \
    libglib2.0-0 \
    wget \
    ffmpeg \
    aria2 \
    rsync \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update --yes && \
    apt-get install --yes --no-install-recommends python3-pip "python${PYTHON_VERSION}" "python${PYTHON_VERSION}-venv" && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen

# Install uv package installer
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
RUN python${PYTHON_VERSION} -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory to root
WORKDIR /

# Install Jupyter and FastAPI dependencies with uv
RUN uv pip install --no-cache \
    jupyter \
    jupyterlab \
    nodejs \
    requests \
    fastapi \
    uvicorn \
    websockets \
    pydantic \
    jinja2 \
    gdown \
    onnxruntime-gpu \
    pip \
    "numpy<2"

# Setup Jupyter configuration
RUN jupyter notebook --generate-config && \
    echo "c.NotebookApp.allow_root = True" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.ip = '0.0.0.0'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.token = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.password = ''" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_origin = '*'" >> /root/.jupyter/jupyter_notebook_config.py && \
    echo "c.NotebookApp.allow_remote_access = True" >> /root/.jupyter/jupyter_notebook_config.py

# clear cache to free up space 
RUN uv cache clean 
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Create workspace directory
RUN mkdir -p /workspace
RUN mkdir -p /notebooks /notebooks/dto /notebooks/static /notebooks/utils /notebooks/workers

# Copy scripts to root
WORKDIR /notebooks
COPY start.sh .
COPY log_viewer.py . 
COPY download_models.py .
COPY ./constants/ ./constants/
COPY ./dto/ ./dto/
COPY ./static/ ./static/
COPY ./workers/ ./workers/
COPY ./utils/ ./utils/
COPY ./templates/ ./templates/

RUN ls -la

COPY models_config.json /workspace

# Make scripts executable
RUN chmod +x *.sh

# Expose ports
EXPOSE 8888 8189

# Clone Stable Diffusion WebUI Forge
RUN git clone --depth=1 https://github.com/lllyasviel/stable-diffusion-webui-forge /workspace/stable-diffusion-webui-forge

# Install Forge dependencies
WORKDIR /workspace/stable-diffusion-webui-forge
RUN uv pip install xformers!=0.0.18 torch==2.5.1 torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
RUN uv pip install -r requirements_versions.txt

# Clone extensions
RUN git clone --depth=1 https://github.com/zanllp/sd-webui-infinite-image-browsing /workspace/stable-diffusion-webui-forge/extensions/sd-webui-infinite-image-browsing
RUN git clone --depth=1 https://github.com/Coyote-A/ultimate-upscale-for-automatic1111 /workspace/stable-diffusion-webui-forge/extensions/ultimateSD
RUN git clone --depth=1 https://github.com/Gourieff/sd-webui-reactor-sfw /workspace/stable-diffusion-webui-forge/extensions/sd-webui-reactor-sfw

# Install extension requirements
WORKDIR /workspace/stable-diffusion-webui-forge/extensions/sd-webui-infinite-image-browsing
RUN pip install -r requirements.txt
#WORKDIR /workspace/stable-diffusion-webui-forge/extensions/sd-webui-reactor-sfw
#RUN pip install -r requirements.txt

WORKDIR /notebooks

# Expose Forge's default port
EXPOSE 7860 

CMD ["./start.sh"]

