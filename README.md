# Hunyuan ComfyUI Docker

A comprehensive Docker setup for running Hunyuan video generation with ComfyUI, featuring real-time monitoring and automatic model management.

## Features

- **Hunyuan Video Generation**: Pre-configured with all necessary models and custom nodes
- **Real-time Monitoring**: Web-based interface for system and process monitoring
- **Dynamic Model Management**: Flexible model downloading system
- **Jupyter Integration**: Built-in Jupyter Lab for development
- **Auto-Update System**: Optional automatic updates for ComfyUI and custom nodes

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/[your-username]/hunyuan-comfyui-docker.git
   cd hunyuan-comfyui-docker
   ```

2. **Configure model sources**:
   - Edit `models_config.json` with your model URLs
   - Place local LORA models in the `models/` directory

3. **Build and run**:
   ```bash
   docker build -t hunyuan-comfyui .
   docker run -d \
     --gpus all \
     -p 8188:8188 \
     -p 8189:8189 \
     -p 8888:8888 \
     hunyuan-comfyui
   ```

## Directory Structure

```
hunyuan-comfyui-docker/
├── Dockerfile
├── models/                    # Local LORA models
├── scripts/
│   ├── download_models.py    # Model download script
│   ├── update.sh            # Update script
│   ├── start.sh             # Startup script
│   └── log_viewer.py        # Monitoring interface
├── models_config.json        # Model download configuration
└── README.md
```

## Accessing Services

- ComfyUI: `http://localhost:8188`
- Log Viewer: `http://localhost:8189`
- Jupyter Lab: `http://localhost:8888`

## Model Configuration

Edit `models_config.json` to configure model downloads:

```json
{
  "diffusion_models": [
    "https://huggingface.co/..."
  ],
  "unet": [
    "https://huggingface.co/..."
  ]
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| UPDATE_ON_START | Enable automatic updates | false |
| MODELS_CONFIG_URL | Custom model config URL | default config |
| SKIP_MODEL_DOWNLOAD | Skip model downloads | false |
| FORCE_MODEL_DOWNLOAD | Force model re-download | false |

## Requirements

- Docker with NVIDIA Container Toolkit
- NVIDIA GPU with CUDA support (RTX 4090 recommended)
- 20GB+ disk space
- 16GB+ RAM

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 